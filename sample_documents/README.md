# EduPath Python Sample Learning Resources

These are original beginner-level learning notes maintained in the EduPath repository. They are provided as starter material for the administrator Knowledge Management workflow.

**Important:** Files in this folder are not imported into Neon at application startup. An administrator can use **Import missing sample resources** in Knowledge Management to import the original nine-note starter pack. The importer checks SHA-256 content hashes, preserves existing resources, and reports archived or incorrectly mapped duplicates. After import, an administrator must generate every missing chunk embedding and review the resource inventory.

## Topic-to-file mapping

| Course topic | Topic slug | Sample resource |
|---|---|---|
| Introduction, Variables and Data Types | `variables-data-types` | `python_variables_intro_sanitized.md` |
| Operators and Expressions | `operators` | `python_operators_expressions.md` |
| Conditional Statements | `conditionals` | `python_conditional_statements.md` |
| Loops | `loops` | `python_loops.md` |
| Functions | `functions` | `python_functions.md` |
| Lists and Tuples | `lists-tuples` | `python_lists_and_tuples.md` |
| Dictionaries and Sets | `dictionaries-sets` | `python_dictionaries_and_sets.md` |
| Strings | `strings` | `python_strings.md` |
| Basic Problem Solving | `problem-solving` | `python_basic_problem_solving.md` |

## Upload metadata

For these repository-authored materials, use the following metadata in Knowledge Management:

- **Source title:** Use the document heading, for example, `Python Loops`.
- **Source license:** `Original — EduPath project`.
- **Rights basis:** `Original work`.
- **Topic association:** Select the matching topic from the table above.

## Recommended upload and verification sequence

1. Sign in with an active administrator account.
2. Open **Knowledge Management** and select **Python Programming**.
3. Click **Import missing sample resources**. The action imports only files whose SHA-256 content hash is not already present in the course.
4. Review the import summary. Resolve any archived or topic-mismatch entries in the resource inventory.
5. Generate missing embeddings for each ready resource.
6. Confirm all nine topics show **Covered** in Topic Resource Coverage and each imported resource has all chunks embedded.
7. Review the source content, examples and exercises before publishing.

The topic coverage check is a technical completeness signal: it confirms that at least one non-archived, ready, topic-specific resource has an embedding for every chunk. It does not automatically judge factual accuracy, pedagogical depth, accessibility or completeness. An administrator should review those qualities before publishing the course.

## Scope

The resources target the existing nine-topic beginner Python curriculum. They are not an advanced Python reference and do not replace instructor review or the course assessment question bank.
