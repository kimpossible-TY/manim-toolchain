import Foundation
import SwiftUI

@MainActor
final class WorkMonitorStore: ObservableObject {
    @Published private(set) var works: [WorkRuntime]
    @Published private(set) var isRefreshing = false
    @Published var selectedWorkID: UUID?

    private let registry: WorkRegistry
    private let client: RunPodStatusClient
    private var refreshTask: Task<Void, Never>?
    private var lastRegistryModification: Date?

    init(registry: WorkRegistry = WorkRegistry(), client: RunPodStatusClient = RunPodStatusClient()) {
        self.registry = registry
        self.client = client
        self.lastRegistryModification = registry.modificationDate
        self.works = registry.load().map { WorkRuntime(configuration: $0) }
    }

    var orderedWorks: [WorkRuntime] {
        works.sorted { lhs, rhs in
            sortPriority(for: lhs) < sortPriority(for: rhs)
        }
    }

    var primaryWork: WorkRuntime? {
        if let selectedWorkID,
           let selected = works.first(where: { $0.id == selectedWorkID }) {
            return selected
        }
        return orderedWorks.first
    }

    var additionalActiveWorkCount: Int {
        max(0, works.filter(\.isActive).count - (primaryWork?.isActive == true ? 1 : 0))
    }

    var pollingInterval: Duration {
        if works.isEmpty {
            return .seconds(30)
        } else if works.contains(where: \.isActive) {
            return .seconds(6)
        } else {
            return .seconds(25)
        }
    }

    func start() {
        guard refreshTask == nil else { return }
        refreshTask = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { break }
                await self.refresh()
                let interval = self.pollingInterval
                try? await Task.sleep(for: interval)
            }
        }
    }

    func refresh() async {
        guard !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }

        syncRegistry()
        let configurations = works.map(\.configuration)
        for configuration in configurations {
            guard !configuration.jobsFilePaths.isEmpty else {
                markRefreshFailure(for: configuration.id)
                continue
            }
            var refreshedPart = false
            var partRefreshFailed = false
            for jobsFilePath in configuration.jobsFilePaths {
                do {
                    let snapshot = try await client.status(for: jobsFilePath)
                    apply(snapshot, to: configuration.id, jobsFilePath: jobsFilePath)
                    refreshedPart = true
                } catch {
                    partRefreshFailed = true
                }
            }
            if refreshedPart {
                recordProgressSample(for: configuration.id)
            }
            if partRefreshFailed || !refreshedPart {
                markRefreshFailure(for: configuration.id)
            } else {
                clearRefreshFailure(for: configuration.id)
            }
        }
    }

    func addWork(name: String, jobsFilePath: String) {
        let configuration = WorkConfiguration(name: name, jobsFilePath: jobsFilePath)
        works.append(WorkRuntime(configuration: configuration))
        selectedWorkID = configuration.id
        persistConfigurations()
        Task { await refresh() }
    }

    func removeWork(id: UUID) {
        works.removeAll { $0.id == id }
        if selectedWorkID == id { selectedWorkID = nil }
        persistConfigurations()
    }

    func selectWork(id: UUID) {
        selectedWorkID = id
    }

    private func apply(_ snapshot: WorkSnapshot, to id: UUID, jobsFilePath: String) {
        guard let index = works.firstIndex(where: { $0.id == id }) else { return }
        var work = works[index]
        if let partIndex = work.partStatuses.firstIndex(where: { $0.jobsFilePath == jobsFilePath }) {
            work.partStatuses[partIndex] = WorkPartStatus(jobsFilePath: jobsFilePath, snapshot: snapshot)
        } else {
            work.partStatuses.append(WorkPartStatus(jobsFilePath: jobsFilePath, snapshot: snapshot))
        }
        works[index] = work
    }

    private func recordProgressSample(for id: UUID) {
        guard let index = works.firstIndex(where: { $0.id == id }),
              let snapshot = works[index].snapshot else { return }
        let now = Date()
        var work = works[index]
        work.progressSamples.append(ProgressSample(date: now, percent: snapshot.progress.percent))
        let cutoff = now.addingTimeInterval(-15 * 60)
        work.progressSamples = Array(work.progressSamples.filter { $0.date >= cutoff }.suffix(180))
        work.eta = snapshot.status == .running
            ? ETAEstimator.estimate(samples: work.progressSamples, currentPercent: snapshot.progress.percent)
            : nil
        works[index] = work
    }

    private func clearRefreshFailure(for id: UUID) {
        guard let index = works.firstIndex(where: { $0.id == id }) else { return }
        works[index].lastRefreshError = false
    }

    private func syncRegistry() {
        let currentMod = registry.modificationDate
        if let lastRegistryModification, let currentMod, lastRegistryModification == currentMod {
            return
        }
        lastRegistryModification = currentMod

        let configurations = registry.load()
        if configurations.isEmpty {
            works = []
            return
        }

        var existing = Dictionary(uniqueKeysWithValues: works.map { ($0.id, $0) })
        works = configurations.map { configuration in
            if var runtime = existing.removeValue(forKey: configuration.id) {
                runtime.configuration = configuration
                return runtime
            }
            return WorkRuntime(configuration: configuration)
        }
    }

    private func markRefreshFailure(for id: UUID) {
        guard let index = works.firstIndex(where: { $0.id == id }) else { return }
        works[index].lastRefreshError = true
    }

    private func persistConfigurations() {
        do {
            try registry.save(works.map(\.configuration))
            lastRegistryModification = registry.modificationDate
        } catch {
            // The monitor remains usable for this session if persistence fails.
        }
    }

    private func sortPriority(for work: WorkRuntime) -> Int {
        switch work.state {
        case .running: 0
        case .queued, .waiting: 1
        case .error: 2
        case .completed: 3
        case nil: 4
        }
    }
}
