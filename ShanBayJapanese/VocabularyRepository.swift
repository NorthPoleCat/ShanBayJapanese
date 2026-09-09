import Foundation
import SQLite3

struct VocabularyItem: Identifiable, Hashable {
    let id: Int64
    let word: String
    let reading: String
    let level: Int
    let primaryPartOfSpeech: String
    let posGroup: String
    let partOfSpeech: String
    let verbClass: String
    let transitivity: String
    let adjectiveClass: String
    let isCommon: Bool
    let meanings: String

    var conjugationTypeLabel: String? {
        guard posGroup == "verb" else { return nil }
        let sourcePOS = primaryPartOfSpeech.lowercased()
        if word.hasSuffix("する") || sourcePOS.hasPrefix("suru verb") {
            return "サ变动词"
        }
        if sourcePOS.contains("kuru verb") {
            return "カ变动词"
        }
        switch verbClass {
        case "godan": return "五段动词"
        case "ichidan": return "一段动词"
        case "irregular": return "不规则动词"
        default: return nil
        }
    }

    var transitivityLabel: String? {
        guard posGroup == "verb" else { return nil }
        switch transitivity {
        case "transitive": return "他动词"
        case "intransitive": return "自动词"
        case "both": return "自动词・他动词"
        default: return nil
        }
    }

    var partOfSpeechLabels: [String] {
        if posGroup == "verb" {
            let labels = [conjugationTypeLabel, transitivityLabel].compactMap { $0 }
            return labels.isEmpty ? ["动词"] : labels
        }
        return partOfSpeech.isEmpty ? [] : [partOfSpeech]
    }
}

struct VocabularySense: Identifiable {
    let id: Int64
    let index: Int
    let meaningChinese: String
    let meaningEnglish: String
    let partOfSpeech: String
}

struct VocabularyExample: Identifiable {
    let id: Int64
    let sentenceJapanese: String
    let sentenceChinese: String
    let sentenceEnglish: String
}

struct VocabularySpelling: Identifiable {
    let id: Int64
    let spelling: String
    let type: String
    let isPrimary: Bool
}

enum VocabularyDatabaseError: LocalizedError {
    case resourceMissing
    case openFailed(String)
    case queryFailed(String)

    var errorDescription: String? {
        switch self {
        case .resourceMissing:
            return "应用内未找到 vocabulary.sqlite"
        case .openFailed(let message):
            return "无法打开词库：\(message)"
        case .queryFailed(let message):
            return "查询词库失败：\(message)"
        }
    }
}

final class VocabularyRepository {
    private var database: OpaquePointer?

    init() throws {
        guard let url = Bundle.main.url(forResource: "vocabulary", withExtension: "sqlite") else {
            throw VocabularyDatabaseError.resourceMissing
        }

        let result = sqlite3_open_v2(url.path, &database, SQLITE_OPEN_READONLY, nil)
        guard result == SQLITE_OK else {
            let message = database.flatMap { String(cString: sqlite3_errmsg($0)) } ?? "未知错误"
            sqlite3_close(database)
            database = nil
            throw VocabularyDatabaseError.openFailed(message)
        }
    }

    deinit {
        sqlite3_close(database)
    }

    func search(text: String, level: Int?, limit: Int = 100) throws -> [VocabularyItem] {
        let normalized = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let escaped = normalized
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "%", with: "\\%")
            .replacingOccurrences(of: "_", with: "\\_")

        let sql = """
        SELECT
            v.id,
            COALESCE(
                (SELECT spelling FROM vocabulary_spellings
                 WHERE vocabulary_id = v.id AND is_primary = 1 LIMIT 1),
                v.word
            ) AS display_word,
            v.reading,
            v.jlpt_level,
            COALESCE(v.primary_pos, ''),
            COALESCE(v.pos_group, ''),
            COALESCE(v.pos_zh, v.pos_group, ''),
            COALESCE(v.verb_class, ''),
            COALESCE(v.transitivity, ''),
            COALESCE(v.adjective_class, ''),
            v.is_common,
            COALESCE(
                NULLIF(GROUP_CONCAT(NULLIF(s.meaning_zh, ''), '；'), ''),
                GROUP_CONCAT(NULLIF(s.meaning_en, ''), '; '),
                ''
            ) AS meanings
        FROM vocabulary v
        LEFT JOIN senses s ON s.vocabulary_id = v.id
        WHERE (?1 IS NULL OR v.jlpt_level = ?1)
          AND (
              ?2 = ''
              OR v.word LIKE ?3 ESCAPE '\\'
              OR v.reading LIKE ?3 ESCAPE '\\'
              OR EXISTS (
                  SELECT 1 FROM vocabulary_spellings matched_spelling
                  WHERE matched_spelling.vocabulary_id = v.id
                    AND matched_spelling.spelling LIKE ?3 ESCAPE '\\'
              )
              OR EXISTS (
                  SELECT 1 FROM senses matched_sense
                  WHERE matched_sense.vocabulary_id = v.id
                    AND (
                        matched_sense.meaning_zh LIKE ?3 ESCAPE '\\'
                        OR matched_sense.meaning_en LIKE ?3 ESCAPE '\\'
                    )
              )
          )
        GROUP BY v.id
        ORDER BY
            CASE WHEN ?2 <> '' AND (
                v.word = ?2 OR v.reading = ?2 OR EXISTS (
                    SELECT 1 FROM vocabulary_spellings exact_spelling
                    WHERE exact_spelling.vocabulary_id = v.id
                      AND exact_spelling.spelling = ?2
                )
            ) THEN 0 ELSE 1 END,
            v.is_common DESC,
            v.common_score DESC,
            v.jlpt_level DESC,
            v.id
        LIMIT ?4
        """

        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VocabularyDatabaseError.queryFailed(lastError)
        }
        defer { sqlite3_finalize(statement) }

        if let level {
            sqlite3_bind_int(statement, 1, Int32(level))
        } else {
            sqlite3_bind_null(statement, 1)
        }
        bind(normalized, to: 2, in: statement)
        bind("%\(escaped)%", to: 3, in: statement)
        sqlite3_bind_int(statement, 4, Int32(limit))

        var items: [VocabularyItem] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            items.append(VocabularyItem(
                id: sqlite3_column_int64(statement, 0),
                word: string(at: 1, in: statement),
                reading: string(at: 2, in: statement),
                level: Int(sqlite3_column_int(statement, 3)),
                primaryPartOfSpeech: string(at: 4, in: statement),
                posGroup: string(at: 5, in: statement),
                partOfSpeech: string(at: 6, in: statement),
                verbClass: string(at: 7, in: statement),
                transitivity: string(at: 8, in: statement),
                adjectiveClass: string(at: 9, in: statement),
                isCommon: sqlite3_column_int(statement, 10) == 1,
                meanings: string(at: 11, in: statement)
            ))
        }

        guard sqlite3_errcode(database) == SQLITE_OK || sqlite3_errcode(database) == SQLITE_DONE else {
            throw VocabularyDatabaseError.queryFailed(lastError)
        }
        return items
    }

    func senses(for vocabularyID: Int64) throws -> [VocabularySense] {
        let sql = """
        SELECT id, jmdict_sense_index,
               COALESCE(meaning_zh, ''), COALESCE(meaning_en, ''),
               COALESCE(pos_zh, pos_group, '')
        FROM senses
        WHERE vocabulary_id = ?1
        ORDER BY jmdict_sense_index
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VocabularyDatabaseError.queryFailed(lastError)
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_int64(statement, 1, vocabularyID)

        var result: [VocabularySense] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            result.append(VocabularySense(
                id: sqlite3_column_int64(statement, 0),
                index: Int(sqlite3_column_int(statement, 1)),
                meaningChinese: string(at: 2, in: statement),
                meaningEnglish: string(at: 3, in: statement),
                partOfSpeech: string(at: 4, in: statement)
            ))
        }
        return result
    }

    func examples(for vocabularyID: Int64) throws -> [VocabularyExample] {
        let sql = """
        SELECT id, sentence_ja, COALESCE(sentence_zh, ''), COALESCE(sentence_en, '')
        FROM examples
        WHERE vocabulary_id = ?1
        ORDER BY id
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VocabularyDatabaseError.queryFailed(lastError)
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_int64(statement, 1, vocabularyID)

        var result: [VocabularyExample] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            result.append(VocabularyExample(
                id: sqlite3_column_int64(statement, 0),
                sentenceJapanese: string(at: 1, in: statement),
                sentenceChinese: string(at: 2, in: statement),
                sentenceEnglish: string(at: 3, in: statement)
            ))
        }
        return result
    }

    func spellings(for vocabularyID: Int64) throws -> [VocabularySpelling] {
        let sql = """
        SELECT id, spelling, spelling_type, is_primary
        FROM vocabulary_spellings
        WHERE vocabulary_id = ?1
        ORDER BY is_primary DESC, priority_score DESC, spelling_type, spelling
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(database, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VocabularyDatabaseError.queryFailed(lastError)
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_int64(statement, 1, vocabularyID)

        var result: [VocabularySpelling] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            result.append(VocabularySpelling(
                id: sqlite3_column_int64(statement, 0),
                spelling: string(at: 1, in: statement),
                type: string(at: 2, in: statement),
                isPrimary: sqlite3_column_int(statement, 3) == 1
            ))
        }
        return result
    }

    private var lastError: String {
        database.map { String(cString: sqlite3_errmsg($0)) } ?? "未知错误"
    }

    private func bind(_ value: String, to index: Int32, in statement: OpaquePointer?) {
        sqlite3_bind_text(statement, index, value, -1, SQLITE_TRANSIENT)
    }

    private func string(at index: Int32, in statement: OpaquePointer?) -> String {
        guard let value = sqlite3_column_text(statement, index) else { return "" }
        return String(cString: value)
    }
}

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
