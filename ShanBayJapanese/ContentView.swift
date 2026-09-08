//
//  ContentView.swift
//  ShanBayJapanese
//
//  Created by xun liu on 2026/9/7.
//

import SwiftUI

struct ContentView: View {
    @State private var searchText = ""
    @State private var selectedLevel: Int? = nil
    @State private var words: [VocabularyItem] = []
    @State private var errorMessage: String?

    private let repository: VocabularyRepository?

    init() {
        do {
            repository = try VocabularyRepository()
        } catch {
            repository = nil
            _errorMessage = State(initialValue: error.localizedDescription)
        }
    }

    var body: some View {
        NavigationStack {
            Group {
                if let errorMessage {
                    ContentUnavailableView(
                        "词库不可用",
                        systemImage: "exclamationmark.triangle",
                        description: Text(errorMessage)
                    )
                } else if words.isEmpty {
                    ContentUnavailableView.search(text: searchText)
                } else {
                    List(words) { item in
                        NavigationLink {
                            VocabularyDetailView(item: item, repository: repository)
                        } label: {
                            VocabularyRow(item: item)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("日语词库")
            .searchable(text: $searchText, prompt: "日文、假名或释义")
            .onSubmit(of: .search, runSearch)
            .onChange(of: searchText) { _, _ in runSearch() }
            .onChange(of: selectedLevel) { _, _ in runSearch() }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button("全部等级") { selectedLevel = nil }
                        Divider()
                        ForEach((1...5).reversed(), id: \.self) { level in
                            Button("N\(level)") { selectedLevel = level }
                        }
                    } label: {
                        Label(selectedLevel.map { "N\($0)" } ?? "全部", systemImage: "line.3.horizontal.decrease.circle")
                    }
                }
            }
        }
        .task {
            runSearch()
        }
    }

    private func runSearch() {
        guard let repository else { return }
        do {
            words = try repository.search(text: searchText, level: selectedLevel)
            errorMessage = nil
        } catch {
            words = []
            errorMessage = error.localizedDescription
        }
    }
}

private struct VocabularyDetailView: View {
    let item: VocabularyItem
    let repository: VocabularyRepository?

    @State private var senses: [VocabularySense] = []
    @State private var examples: [VocabularyExample] = []
    @State private var errorMessage: String?

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text(item.word)
                        .font(.largeTitle.bold())
                    if !item.reading.isEmpty && item.reading != item.word {
                        Text(item.reading)
                            .font(.title3)
                            .foregroundStyle(.secondary)
                    }
                    HStack(spacing: 10) {
                        Text("JLPT N\(item.level)")
                        if !item.partOfSpeech.isEmpty {
                            Text(item.partOfSpeech)
                        }
                        if item.isCommon {
                            Label("常用", systemImage: "star.fill")
                        }
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
                .padding(.vertical, 6)
            }

            Section("释义") {
                if senses.isEmpty {
                    Text("暂无释义")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(senses) { sense in
                        VStack(alignment: .leading, spacing: 5) {
                            HStack(alignment: .firstTextBaseline) {
                                Text("\(sense.index + 1).")
                                    .foregroundStyle(.secondary)
                                Text(sense.meaningChinese.isEmpty ? sense.meaningEnglish : sense.meaningChinese)
                            }
                            if !sense.meaningChinese.isEmpty && !sense.meaningEnglish.isEmpty {
                                Text(sense.meaningEnglish)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            if !sense.partOfSpeech.isEmpty && sense.partOfSpeech != item.partOfSpeech {
                                Text(sense.partOfSpeech)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 3)
                    }
                }
            }

            Section("例句") {
                if examples.isEmpty {
                    Text("这个词目前没有收录例句")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(examples) { example in
                        VStack(alignment: .leading, spacing: 7) {
                            Text(example.sentenceJapanese)
                                .font(.body)
                            if !example.sentenceChinese.isEmpty {
                                Text(example.sentenceChinese)
                                    .foregroundStyle(.secondary)
                            }
                            if !example.sentenceEnglish.isEmpty {
                                Text(example.sentenceEnglish)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            if let errorMessage {
                Section {
                    Label(errorMessage, systemImage: "exclamationmark.triangle")
                        .foregroundStyle(.red)
                }
            }
        }
        .navigationTitle(item.word)
        .navigationBarTitleDisplayMode(.inline)
        .task { loadDetails() }
    }

    private func loadDetails() {
        guard let repository else { return }
        do {
            senses = try repository.senses(for: item.id)
            examples = try repository.examples(for: item.id)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

private struct VocabularyRow: View {
    let item: VocabularyItem

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(alignment: .firstTextBaseline) {
                Text(item.word)
                    .font(.title3.weight(.semibold))

                if !item.reading.isEmpty && item.reading != item.word {
                    Text(item.reading)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Text("N\(item.level)")
                    .font(.caption.bold())
                    .foregroundStyle(levelColor)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(levelColor.opacity(0.12), in: Capsule())
            }

            if !item.meanings.isEmpty {
                Text(item.meanings)
                    .font(.subheadline)
                    .foregroundStyle(.primary)
                    .lineLimit(3)
            }

            HStack(spacing: 8) {
                if !item.partOfSpeech.isEmpty {
                    Text(item.partOfSpeech)
                }
                if item.isCommon {
                    Label("常用", systemImage: "star.fill")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 5)
    }

    private var levelColor: Color {
        switch item.level {
        case 5: .green
        case 4: .teal
        case 3: .blue
        case 2: .orange
        default: .red
        }
    }
}
