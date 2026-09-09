//
//  ContentView.swift
//  ShanBayJapanese
//
//  Created by xun liu on 2026/9/7.
//

import SwiftUI
import AVFoundation

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
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.dismiss) private var dismiss

    let item: VocabularyItem
    let repository: VocabularyRepository?

    @State private var senses: [VocabularySense] = []
    @State private var examples: [VocabularyExample] = []
    @State private var errorMessage: String?
    @State private var isConjugationsExpanded = false
    @State private var speechSynthesizer = AVSpeechSynthesizer()

    private var conjugations: [ConjugationForm] {
        JapaneseConjugator.forms(for: item)
    }

    private var themeColor: Color {
        colorScheme == .dark
            ? Color(red: 0.4, green: 0.7, blue: 1.0)
            : Color(red: 0.2, green: 0.6, blue: 1.0)
    }

    var body: some View {
        VStack(spacing: 0) {
            detailHeader

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text(item.word)
                            .font(.title2.bold())
                        if !item.reading.isEmpty && item.reading != item.word {
                            Text("（\(item.reading)）")
                                .font(.body)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.bottom, 10)

                    meaningsView

                    HStack(spacing: 8) {
                        detailTag("JLPT N\(item.level)", color: themeColor)
                        if !item.partOfSpeech.isEmpty {
                            detailTag(item.partOfSpeech, color: partOfSpeechColor)
                        }
                        if item.isCommon {
                            detailTag("常用", color: .orange, systemImage: "star.fill")
                        }
                    }
                    .padding(.top, 14)

                    Divider()
                        .padding(.vertical, 16)

                    if !conjugations.isEmpty {
                        conjugationsView
                        Divider()
                            .padding(.vertical, 16)
                    }

                    examplesView

                    if let errorMessage {
                        Label(errorMessage, systemImage: "exclamationmark.triangle")
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .padding(.top, 16)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 16)
                .padding(.vertical, 18)
            }
        }
        .background(Color(uiColor: .systemBackground))
        .toolbar(.hidden, for: .navigationBar)
        .task { loadDetails() }
        .onDisappear {
            speechSynthesizer.stopSpeaking(at: .immediate)
        }
    }

    private var detailHeader: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.headline)
                    .frame(width: 44, height: 44)
            }

            Spacer()

            Text("单词详情")
                .font(.headline)

            Spacer()

            Button {
                playAudio()
            } label: {
                Image(systemName: "speaker.wave.2.fill")
                    .font(.headline)
                    .frame(width: 44, height: 44)
            }
        }
        .foregroundStyle(.white)
        .padding(.horizontal, 4)
        .background(themeColor.ignoresSafeArea(edges: .top))
    }

    @ViewBuilder
    private var meaningsView: some View {
        if senses.isEmpty {
            Text("暂无释义")
                .foregroundStyle(.secondary)
        } else {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(senses) { sense in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(alignment: .firstTextBaseline, spacing: 6) {
                            if senses.count > 1 {
                                Text("\(sense.index + 1).")
                                    .foregroundStyle(.secondary)
                            }
                            Text(sense.meaningChinese.isEmpty ? sense.meaningEnglish : sense.meaningChinese)
                        }
                        if !sense.meaningChinese.isEmpty && !sense.meaningEnglish.isEmpty {
                            Text(sense.meaningEnglish)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .padding(.leading, senses.count > 1 ? 20 : 0)
                        }
                    }
                }
            }
        }
    }

    private var conjugationsView: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    isConjugationsExpanded.toggle()
                }
            } label: {
                HStack {
                    Text("变形")
                        .font(.headline)
                        .foregroundStyle(themeColor)
                    Spacer()
                    Text("\(conjugations.count)种")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Image(systemName: isConjugationsExpanded ? "chevron.up" : "chevron.down")
                        .font(.caption.bold())
                        .foregroundStyle(themeColor)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if isConjugationsExpanded {
                ForEach(conjugations) { form in
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        Text(form.name)
                            .font(.subheadline)
                            .padding(.vertical, 4)
                            .padding(.horizontal, 7)
                            .foregroundStyle(.white)
                            .background(themeColor, in: RoundedRectangle(cornerRadius: 5))
                        Spacer()
                        Text(form.value)
                            .font(.body.weight(.medium))
                            .multilineTextAlignment(.trailing)
                            .textSelection(.enabled)
                    }
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    @ViewBuilder
    private var examplesView: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("例句")
                .font(.headline)
                .foregroundStyle(themeColor)

            if examples.isEmpty {
                Text("这个词目前没有收录例句")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(examples.enumerated()), id: \.element.id) { index, example in
                    VStack(alignment: .leading, spacing: 7) {
                        Text(example.sentenceJapanese)
                            .font(.body)
                        if !example.sentenceChinese.isEmpty {
                            Text(example.sentenceChinese)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        if !example.sentenceEnglish.isEmpty {
                            Text(example.sentenceEnglish)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    if index < examples.count - 1 {
                        Divider()
                    }
                }
            }
        }
    }

    private func detailTag(_ title: String, color: Color, systemImage: String? = nil) -> some View {
        HStack(spacing: 4) {
            if let systemImage {
                Image(systemName: systemImage)
            }
            Text(title)
        }
        .font(.caption)
        .padding(.vertical, 4)
        .padding(.horizontal, 7)
        .foregroundStyle(.white)
        .background(color, in: RoundedRectangle(cornerRadius: 5))
    }

    private var partOfSpeechColor: Color {
        switch item.posGroup {
        case "verb": Color(red: 0.91, green: 0.42, blue: 0.54)
        case "adjective": Color(red: 0.33, green: 0.72, blue: 0.52)
        default: .gray
        }
    }

    private func playAudio() {
        let target = item.word.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !target.isEmpty else { return }
        speechSynthesizer.stopSpeaking(at: .immediate)
        let utterance = AVSpeechUtterance(string: target)
        utterance.voice = AVSpeechSynthesisVoice(language: "ja-JP")
        utterance.rate = 0.46
        speechSynthesizer.speak(utterance)
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
