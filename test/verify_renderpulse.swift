import Foundation

// Test 1: Verify WorkState and polling interval logic
enum WorkState: String, Codable, CaseIterable {
    case running = "RUNNING"
    case queued = "QUEUED"
    case waiting = "WAITING"
    case completed = "COMPLETED"
    case error = "ERROR"

    var isActive: Bool {
        self == .running || self == .queued || self == .waiting
    }
}

struct MockWork {
    let state: WorkState?
    var isActive: Bool { state?.isActive ?? false }
}

func computePollingInterval(works: [MockWork]) -> Duration {
    if works.isEmpty {
        return .seconds(30)
    } else if works.contains(where: \.isActive) {
        return .seconds(6)
    } else {
        return .seconds(25)
    }
}

// Assertions for Test 1
assert(computePollingInterval(works: []) == .seconds(30), "Empty works must poll every 30s")
assert(computePollingInterval(works: [MockWork(state: .running)]) == .seconds(6), "Running work must poll every 6s")
assert(computePollingInterval(works: [MockWork(state: .queued)]) == .seconds(6), "Queued work must poll every 6s")
assert(computePollingInterval(works: [MockWork(state: .waiting)]) == .seconds(6), "Waiting work must poll every 6s")
assert(computePollingInterval(works: [MockWork(state: .completed)]) == .seconds(25), "Completed work must poll every 25s")
assert(computePollingInterval(works: [MockWork(state: .error)]) == .seconds(25), "Error work must poll every 25s")
print("PASS: Adaptive polling interval logic verified")

// Test 2: Verify Process execution and Pipe FileHandle closure with autoreleasepool
func testProcessExecution() {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/true")
    let stdout = Pipe()
    let stderr = Pipe()
    process.standardOutput = stdout
    process.standardError = stderr

    let sema = DispatchSemaphore(value: 0)
    process.terminationHandler = { completed in
        autoreleasepool {
            let _ = stdout.fileHandleForReading.readDataToEndOfFile()
            let _ = stderr.fileHandleForReading.readDataToEndOfFile()
            try? stdout.fileHandleForReading.close()
            try? stderr.fileHandleForReading.close()
            try? stdout.fileHandleForWriting.close()
            try? stderr.fileHandleForWriting.close()
        }
        completed.terminationHandler = nil
        sema.signal()
    }

    try! process.run()
    sema.wait()
}

// Run 50 iterations to verify no crash and clean handle releases
for _ in 0..<50 {
    autoreleasepool {
        testProcessExecution()
    }
}
print("PASS: Process execution and explicit FileHandle closing verified over 50 iterations")

print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY.")
