import Foundation

enum RunPodStatusClientError: LocalizedError {
    case executableMissing(URL)
    case launchFailed(Error)
    case invalidResponse(String)

    var errorDescription: String? {
        switch self {
        case .executableMissing:
            "RenderPulse could not find visual-runpod. Set RENDER_PULSE_RUNPOD_PATH or install the wrapper in ~/.local/bin."
        case .launchFailed:
            "RenderPulse could not start visual-runpod."
        case .invalidResponse:
            "visual-runpod did not return a valid work status."
        }
    }
}

private struct CommandOutput {
    let stdout: Data
    let stderr: Data
    let status: Int32
}

struct RunPodStatusClient {
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
        try await withCheckedThrowingContinuation { continuation in
            autoreleasepool {
                let process = Process()
                process.executableURL = executableURL
                process.arguments = arguments

                let stdout = Pipe()
                let stderr = Pipe()
                process.standardOutput = stdout
                process.standardError = stderr
                process.terminationHandler = { completed in
                    let result = autoreleasepool { () -> CommandOutput in
                        let stdoutData = stdout.fileHandleForReading.readDataToEndOfFile()
                        let stderrData = stderr.fileHandleForReading.readDataToEndOfFile()

                        try? stdout.fileHandleForReading.close()
                        try? stderr.fileHandleForReading.close()
                        try? stdout.fileHandleForWriting.close()
                        try? stderr.fileHandleForWriting.close()

                        return CommandOutput(
                            stdout: stdoutData,
                            stderr: stderrData,
                            status: completed.terminationStatus
                        )
                    }
                    completed.terminationHandler = nil
                    continuation.resume(returning: result)
                }

                do {
                    try process.run()
                } catch {
                    try? stdout.fileHandleForReading.close()
                    try? stderr.fileHandleForReading.close()
                    try? stdout.fileHandleForWriting.close()
                    try? stderr.fileHandleForWriting.close()
                    process.terminationHandler = nil
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
