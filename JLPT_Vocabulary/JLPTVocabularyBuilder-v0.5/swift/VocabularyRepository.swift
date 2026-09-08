import Foundation
import SQLite3

struct VocabularySense: Identifiable {
    let id: Int64
    let senseIndex: Int
    let meaningEN: String?
    let meaningZH: String?
    let reviewStatus: String
}

struct Vocabulary: Identifiable {
    let id: Int64
    let word: String
    let reading: String
    let jlptLevel: Int
    let posGroup: String?
    let verbClass: String?
    let transitivity: String?
    let adjectiveClass: String?
}

final class VocabularyRepository {
    private var db: OpaquePointer?

    init(databaseURL: URL) throws {
        guard sqlite3_open_v2(databaseURL.path, &db, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
            throw NSError(domain: "VocabularyDB", code: 1)
        }
    }

    deinit { sqlite3_close(db) }

    func words(level: Int, limit: Int = 1000) throws -> [Vocabulary] {
        let sql = """
        SELECT id,word,reading,jlpt_level,pos_group,verb_class,transitivity,adjective_class
        FROM vocabulary
        WHERE jlpt_level=?
        ORDER BY id
        LIMIT ?
        """
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            throw NSError(domain: "VocabularyDB", code: 2)
        }
        defer { sqlite3_finalize(stmt) }

        sqlite3_bind_int(stmt, 1, Int32(level))
        sqlite3_bind_int(stmt, 2, Int32(limit))

        var result: [Vocabulary] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            func str(_ i: Int32) -> String? {
                guard let c = sqlite3_column_text(stmt, i) else { return nil }
                return String(cString: c)
            }
            result.append(.init(
                id: sqlite3_column_int64(stmt, 0),
                word: str(1) ?? "",
                reading: str(2) ?? "",
                jlptLevel: Int(sqlite3_column_int(stmt, 3)),
                posGroup: str(4),
                verbClass: str(5),
                transitivity: str(6),
                adjectiveClass: str(7)
            ))
        }
        return result
    }

    func senses(vocabularyID: Int64) throws -> [VocabularySense] {
        let sql = """
        SELECT id,jmdict_sense_index,meaning_en,meaning_zh,review_status
        FROM senses
        WHERE vocabulary_id=?
        ORDER BY jmdict_sense_index
        """
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            throw NSError(domain: "VocabularyDB", code: 3)
        }
        defer { sqlite3_finalize(stmt) }

        sqlite3_bind_int64(stmt, 1, vocabularyID)

        var result: [VocabularySense] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            func str(_ i: Int32) -> String? {
                guard let c = sqlite3_column_text(stmt, i) else { return nil }
                return String(cString: c)
            }
            result.append(.init(
                id: sqlite3_column_int64(stmt, 0),
                senseIndex: Int(sqlite3_column_int(stmt, 1)),
                meaningEN: str(2),
                meaningZH: str(3),
                reviewStatus: str(4) ?? "pending"
            ))
        }
        return result
    }
}
