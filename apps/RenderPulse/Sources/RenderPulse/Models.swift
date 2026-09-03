import Foundation

struct WorkConfiguration: Codable, Hashable, Identifiable {
    let id: UUID
    var name: String
    var jobsFilePaths: [String]
    let createdAt: Date

    init(id: UUID = UUID(), name: String, jobsFilePath: String, createdAt: Date = .now) {
        self.id = id
        self.name = name
        self.jobsFilePaths = [jobsFilePath]
        self.createdAt = createdAt
    }

    init(id: UUID = UUID(), name: String, jobsFilePaths: [String], createdAt: Date = .now) {
        self.id = id
        self.name = name
        self.jobsFilePaths = jobsFilePaths
        self.createdAt = createdAt
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case jobsFilePaths = "jobs_file_paths"
        case legacyJobsFilePath = "jobs_file_path"
        case createdAt = "created_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        if let paths = try container.decodeIfPresent([String].self, forKey: .jobsFilePaths) {
            jobsFilePaths = paths
        } else if let path = try container.decodeIfPresent(String.self, forKey: .legacyJobsFilePath) {
            jobsFilePaths = [path]
        } else {
            jobsFilePaths = []
        }
        createdAt = try container.decode(Date.self, forKey: .createdAt)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(jobsFilePaths, forKey: .jobsFilePaths)
        try container.encode(createdAt, forKey: .createdAt)
    }
}

enum WorkState: String, Codable, CaseIterable {
    case running = "RUNNING"
    case queued = "QUEUED"
    case waiting = "WAITING"
    case completed = "COMPLETED"
    case error = "ERROR"

    var label: String {
        switch self {
        case .running: "Running"
        case .queued: "Queued"
        case .waiting: "Waiting"
        case .completed: "Completed"
        case .error: "Error"
        }
    }

    var isActive: Bool {
        self == .running || self == .queued || self == .waiting
    }
}

struct WorkProgress: Codable, Equatable {
    let percent: Double
    let framesCompleted: Int
    let framesTotal: Int
}

struct WorkerCounts: Codable, Equatable {
    let active: Int
    let queued: Int
    let total: Int
}

struct CountSummary: Codable, Equatable {
    let count: Int
}

struct WorkSnapshot: Codable, Equatable {
    let schemaVersion: Int
    let status: WorkState
    let progress: WorkProgress
    let workers: WorkerCounts
    let warnings: CountSummary
    let errors: CountSummary
    let updatedAt: String
}

struct ProgressSample: Equatable {
    let date: Date
    let percent: Double
}

struct WorkPartStatus: Equatable {
    let jobsFilePath: String
    let snapshot: WorkSnapshot
}

struct WorkRuntime: Identifiable {
    var configuration: WorkConfiguration
    var partStatuses: [WorkPartStatus] = []
    var eta: TimeInterval?
    var lastRefreshError: Bool = false
    var progressSamples: [ProgressSample] = []

    var id: UUID { configuration.id }

    var snapshot: WorkSnapshot? {
        guard !partStatuses.isEmpty else { return nil }

        let progressFrames = partStatuses.reduce(0) { $0 + $1.snapshot.progress.framesCompleted }
        let totalFrames = partStatuses.reduce(0) { $0 + $1.snapshot.progress.framesTotal }
        let percent = totalFrames > 0
            ? round(Double(progressFrames) / Double(totalFrames) * 1000) / 10
            : 0
        let workers = partStatuses.reduce(
            into: WorkerCounts(active: 0, queued: 0, total: 0)
        ) { result, part in
            result = WorkerCounts(
                active: result.active + part.snapshot.workers.active,
                queued: result.queued + part.snapshot.workers.queued,
                total: result.total + part.snapshot.workers.total
            )
        }
        let warnings = partStatuses.reduce(0) { $0 + $1.snapshot.warnings.count }
        let errors = partStatuses.reduce(0) { $0 + $1.snapshot.errors.count }
        let state: WorkState
        if partStatuses.contains(where: { $0.snapshot.status == .error }) {
            state = .error
        } else if partStatuses.allSatisfy({ $0.snapshot.status == .completed }) {
            state = .completed
        } else if partStatuses.contains(where: { $0.snapshot.status == .running }) {
            state = .running
        } else if partStatuses.contains(where: { $0.snapshot.status == .queued }) {
            state = .queued
        } else {
            state = .waiting
        }

        return WorkSnapshot(
            schemaVersion: 1,
            status: state,
            progress: WorkProgress(
                percent: percent,
                framesCompleted: progressFrames,
                framesTotal: totalFrames
            ),
            workers: workers,
            warnings: CountSummary(count: warnings),
            errors: CountSummary(count: errors),
            updatedAt: partStatuses.map(\.snapshot.updatedAt).max() ?? ""
        )
    }

    var state: WorkState? { snapshot?.status }

    var isActive: Bool { state?.isActive ?? false }

    var percent: Double { snapshot?.progress.percent ?? 0 }
}

enum ETAEstimator {
    static func estimate(samples: [ProgressSample], currentPercent: Double) -> TimeInterval? {
        guard currentPercent > 0, currentPercent < 100, samples.count >= 2 else {
            return nil
        }
        guard let first = samples.first, let last = samples.last else { return nil }

        let elapsed = last.date.timeIntervalSince(first.date)
        let gainedPercent = last.percent - first.percent
        guard elapsed >= 20, gainedPercent > 0 else { return nil }

        let secondsPerPercent = elapsed / gainedPercent
        let estimate = secondsPerPercent * (100 - currentPercent)
        // Suppress implausible estimates rather than presenting false precision.
        guard estimate.isFinite, estimate > 0, estimate < 7 * 24 * 60 * 60 else { return nil }
        return estimate
    }
}

enum ETAFormatter {
    static func string(for eta: TimeInterval?) -> String {
        guard let eta else { return "Calculating…" }
        let totalMinutes = max(1, Int(eta.rounded(.up) / 60))
        if totalMinutes < 60 { return "\(totalMinutes)m" }
        return "\(totalMinutes / 60)h \(totalMinutes % 60)m"
    }
}
