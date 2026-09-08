import Foundation
import SQLite3

struct Vocabulary: Identifiable {
    let id: Int64
    let word: String
    let reading: String
    let jlptLevel: Int
    let meaningZH: String?
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
        SELECT v.id, v.word, v.reading, v.jlpt_level,
               (SELECT group_concat(m.meaning, '；')
                FROM meanings m
                WHERE m.vocabulary_id=v.id AND m.language='zh-Hans')
        FROM vocabulary v
        WHERE v.jlpt_level=?
        ORDER BY v.id
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
            let meaning = sqlite3_column_text(stmt, 4).map { String(cString: $0) }
            result.append(.init(
                id: sqlite3_column_int64(stmt, 0),
                word: String(cString: sqlite3_column_text(stmt, 1)),
                reading: String(cString: sqlite3_column_text(stmt, 2)),
                jlptLevel: Int(sqlite3_column_int(stmt, 3)),
                meaningZH: meaning
            ))
        }
        return result
    }
}
