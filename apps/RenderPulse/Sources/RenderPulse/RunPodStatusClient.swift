import Foundation

enum RunPodStatusClientError: LocalizedError {
    case executableMissing(URL)
    case launchFailed(Error)
    case invalidResponse(String)
    case timedOut

    var errorDescription: String? {
        switch self {
        case .executableMissing:
            "RenderPulse could not find visual-runpod. Set RENDER_PULSE_RUNPOD_PATH or install the wrapper in ~/.local/bin."
        case .launchFailed:
            "RenderPulse could not start visual-runpod."
        case .invalidResponse:
            "visual-runpod did not return a valid work status."
        case .timedOut:
            "visual-runpod did not finish within 30 seconds."
        }
    }
}

private struct CommandOutput {
    let stdout: Data
    let stderr: Data
    let status: Int32
}

private final class RunningProcessBox: @unchecked Sendable {
    private enum StopReason {
        case active
        case cancelled
        case timedOut
    }

    private let lock = NSLock()
    private var process: Process?
    private var stopReason: StopReason = .active

    func attach(_ process: Process) -> Bool {
        lock.lock()
        self.process = process
        let shouldStart = stopReason == .active
        lock.unlock()
        return shouldStart
    }

    func cancel() {
        stop(with: .cancelled)
    }

    func timeOut() {
        stop(with: .timedOut)
    }

    func terminationError() -> Error? {
        lock.lock()
        let reason = stopReason
        lock.unlock()

        switch reason {
        case .active:
            return nil
        case .cancelled:
            return CancellationError()
        case .timedOut:
            return RunPodStatusClientError.timedOut
        }
    }

    func clear() {
        lock.lock()
        process = nil
        lock.unlock()
    }

    private func stop(with reason: StopReason) {
        lock.lock()
        guard stopReason == .active else {
            lock.unlock()
            return
        }
        stopReason = reason
        let process = process
        lock.unlock()

        if process?.isRunning == true {
            process?.terminate()
        }
    }
}

struct RunPodStatusClient {
    private static let commandTimeout: TimeInterval = 30

    let executableURL: URL

    init(executableURL: URL? = nil) {
        self.executableURL = executableURL ?? Self.defaultExecutableURL()
    }

    func status(for jobsFilePath: String) async throws -> WorkSnapshot {
        guard FileManager.default.isExecutableFile(atPath: executableURL.path) else {
            throw RunPodStatusClientError.executableMissing(executableURL)
        }

        let output = try await run(
            arguments: [
                "status",
                "--jobs-file", jobsFilePath,
                "--stream",
                "--json",
            ]
        )

        return try autoreleasepool {
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            if let snapshot = try? decoder.decode(WorkSnapshot.self, from: output.stdout) {
                // A failed Pod correctly returns a nonzero CLI status, but its
                // JSON payload still contains a useful work-level error state.
                return snapshot
            }

            let standardError = String(data: output.stderr, encoding: .utf8) ?? ""
            throw RunPodStatusClientError.invalidResponse(standardError)
        }
    }

    private func run(arguments: [String]) async throws -> CommandOutput {
        let processBox = RunningProcessBox()
        return try await withTaskCancellationHandler(operation: {
            try Task.checkCancellation()
            return try await run(arguments: arguments, processBox: processBox)
        }, onCancel: {
            processBox.cancel()
        })
    }

    private func run(
        arguments: [String],
        processBox: RunningProcessBox
    ) async throws -> CommandOutput {
        try await withCheckedThrowingContinuation { continuation in
            autoreleasepool {
                let fileManager = FileManager.default
                let temporaryDirectory = fileManager.temporaryDirectory
                    .appendingPathComponent("RenderPulse-\(UUID().uuidString)", isDirectory: true)
                let stdoutURL = temporaryDirectory.appendingPathComponent("stdout")
                let stderrURL = temporaryDirectory.appendingPathComponent("stderr")

                do {
                    try fileManager.createDirectory(
                        at: temporaryDirectory,
                        withIntermediateDirectories: true
                    )
                    _ = fileManager.createFile(atPath: stdoutURL.path, contents: nil)
                    _ = fileManager.createFile(atPath: stderrURL.path, contents: nil)

                    let stdout = try FileHandle(forWritingTo: stdoutURL)
                    let stderr = try FileHandle(forWritingTo: stderrURL)
                    let process = Process()
                    process.executableURL = executableURL
                    process.arguments = arguments
                    process.standardOutput = stdout
                    process.standardError = stderr

                    guard processBox.attach(process) else {
                        try? stdout.close()
                        try? stderr.close()
                        try? fileManager.removeItem(at: temporaryDirectory)
                        continuation.resume(throwing: CancellationError())
                        return
                    }

                    process.terminationHandler = { completed in
                        let result = autoreleasepool { () -> Result<CommandOutput, Error> in
                            try? stdout.close()
                            try? stderr.close()
                            defer {
                                try? FileManager.default.removeItem(at: temporaryDirectory)
                            }

                            if let error = processBox.terminationError() {
                                return .failure(error)
                            }

                            do {
                                return .success(
                                    CommandOutput(
                                        stdout: try Data(contentsOf: stdoutURL),
                                        stderr: try Data(contentsOf: stderrURL),
                                        status: completed.terminationStatus
                                    )
                                )
                            } catch {
                                return .failure(RunPodStatusClientError.launchFailed(error))
                            }
                        }
                        completed.terminationHandler = nil
                        processBox.clear()
                        continuation.resume(with: result)
                    }

                    try process.run()
                    DispatchQueue.global(qos: .utility).asyncAfter(
                        deadline: .now() + Self.commandTimeout
                    ) {
                        processBox.timeOut()
                    }
                    if processBox.terminationError() != nil, process.isRunning {
                        process.terminate()
                    }
                } catch {
                    processBox.clear()
                    try? fileManager.removeItem(at: temporaryDirectory)
                    continuation.resume(throwing: RunPodStatusClientError.launchFailed(error))
                }
            }
        }
    }

    private static func defaultExecutableURL() -> URL {
        let environment = ProcessInfo.processInfo.environment
        if let configured = environment["RENDER_PULSE_RUNPOD_PATH"], !configured.isEmpty {
            return URL(fileURLWithPath: configured)
        }

        let home = FileManager.default.homeDirectoryForCurrentUser
        var candidates = [
            home.appendingPathComponent(".local/bin/visual-runpod"),
            URL(fileURLWithPath: "/usr/local/bin/visual-runpod"),
            URL(fileURLWithPath: "/opt/homebrew/bin/visual-runpod"),
        ]
        var checkoutDirectory = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        for _ in 0 ..< 5 {
            candidates.append(checkoutDirectory.appendingPathComponent("bin/visual-runpod"))
            checkoutDirectory.deleteLastPathComponent()
        }
        return candidates.first(where: { FileManager.default.isExecutableFile(atPath: $0.path) })
            ?? candidates[0]
    }
}
