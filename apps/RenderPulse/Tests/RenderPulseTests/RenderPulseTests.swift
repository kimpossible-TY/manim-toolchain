import XCTest
@testable import RenderPulse

final class RenderPulseTests: XCTestCase {
    func testStatusPayloadDecodesFromRunPodJSON() throws {
        let data = """
        {
          "schema_version": 1,
          "status": "RUNNING",
          "progress": {"percent": 72.5, "frames_completed": 145, "frames_total": 200},
          "workers": {"active": 4, "queued": 1, "total": 5},
          "warnings": {"count": 2},
          "errors": {"count": 0},
          "updated_at": "2026-09-02T12:00:00+00:00"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let snapshot = try decoder.decode(WorkSnapshot.self, from: data)

        XCTAssertEqual(snapshot.status, .running)
        XCTAssertEqual(snapshot.progress.percent, 72.5)
        XCTAssertEqual(snapshot.workers.active, 4)
        XCTAssertEqual(snapshot.warnings.count, 2)
    }

    func testETAUsesObservedProgressRate() {
        let start = Date(timeIntervalSinceReferenceDate: 1_000)
        let eta = ETAEstimator.estimate(
            samples: [
                ProgressSample(date: start, percent: 20),
                ProgressSample(date: start.addingTimeInterval(40), percent: 30),
            ],
            currentPercent: 30
        )

        XCTAssertEqual(eta, 280, accuracy: 0.001)
    }

    func testETASuppressesAStaticProgressReading() {
        let start = Date(timeIntervalSinceReferenceDate: 1_000)
        XCTAssertNil(
            ETAEstimator.estimate(
                samples: [
                    ProgressSample(date: start, percent: 20),
                    ProgressSample(date: start.addingTimeInterval(40), percent: 20),
                ],
                currentPercent: 20
            )
        )
    }

    func testPollingIntervalUsesTheLowestSafeFrequency() {
        let configuration = WorkConfiguration(
            name: "Render",
            jobsFilePath: "/tmp/runpod.jobs.json"
        )
        let idleWork = WorkRuntime(configuration: configuration)
        let runningSnapshot = WorkSnapshot(
            schemaVersion: 1,
            status: .running,
            progress: WorkProgress(percent: 10, framesCompleted: 1, framesTotal: 10),
            workers: WorkerCounts(active: 1, queued: 0, total: 1),
            warnings: CountSummary(count: 0),
            errors: CountSummary(count: 0),
            updatedAt: ""
        )
        var runningWork = WorkRuntime(configuration: configuration)
        runningWork.partStatuses = [
            WorkPartStatus(
                jobsFilePath: configuration.jobsFilePath,
                snapshot: runningSnapshot
            ),
        ]

        XCTAssertEqual(WorkMonitorStore.pollingInterval(for: []), .seconds(30))
        XCTAssertEqual(WorkMonitorStore.pollingInterval(for: [idleWork]), .seconds(25))
        XCTAssertEqual(WorkMonitorStore.pollingInterval(for: [runningWork]), .seconds(6))
    }
}
