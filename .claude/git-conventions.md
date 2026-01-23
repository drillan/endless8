# Git Conventions

このファイルはプロジェクトのGit命名規則を定義するSingle Source of Truth（正式ソース）です。

## Branch Naming

### Format

```
<issue-number>-<description>
```

または type prefix 付き:

```
<type>/<issue-number>-<description>
```

### Type Prefixes (Optional)

| タイプ | プレフィックス | 用途 |
|--------|---------------|------|
| 機能追加 | `feat/` | 新機能の実装 |
| バグ修正 | `fix/` | バグの修正 |
| リファクタリング | `refactor/` | コードの整理・改善 |
| ドキュメント | `docs/` | ドキュメントの追加・修正 |
| テスト | `test/` | テストの追加・修正 |
| 雑務 | `chore/` | 設定変更、依存関係更新など |

### Issue Number

- **ゼロパディングなし**: `1`（正）、`001`（誤）
- issue番号がない場合は省略可: `feat/add-logging`

**注意**: specs/ ディレクトリはゼロパディングあり（`001-engine-core`）だが、Gitブランチはゼロパディングなし（`1-engine-core`）

### Description

- 英語で記述
- ハイフン区切り（kebab-case）
- 2-4語程度の簡潔な説明
- 小文字のみ
- ブランチ名全体で40文字以内

### Examples

```
1-endless8-engine-core
feat/2-add-reception-agent
fix/3-fix-history-parsing
refactor/4-cleanup-executor
docs/5-update-readme
test/6-add-integration-tests
chore/7-update-dependencies
```

## Commit Message

### Format

[Conventional Commits](https://www.conventionalcommits.org/) 形式に従う:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Type

ブランチプレフィックスと同一:
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `refactor`: リファクタリング
- `test`: テスト
- `chore`: その他

### Scope（任意）

- issue番号: `feat(#1): add engine core`
- モジュール名: `fix(executor): handle timeout error`
- エージェント名: `feat(reception): add validation`

### Description

- 英語で記述
- 命令形（imperative mood）: "add" not "added"
- 小文字で開始
- 末尾にピリオドを付けない

### Examples

```
feat(#1): add engine core implementation

fix(executor): handle session expiration correctly

docs: update installation guide

refactor(#2): extract common validation logic

chore: update dependencies to latest versions
```

## Git Worktree

### Format

```
../<project-name>-<branch-name>
```

### Rules

- 配置場所: メインリポジトリの親ディレクトリ
- プロジェクト名: `endless8`
- ブランチ名: `/` を `-` に置換

### Examples

| ブランチ | ワークツリーディレクトリ |
|---------|------------------------|
| `1-engine-core` | `../endless8-1-engine-core` |
| `feat/2-add-auth` | `../endless8-feat-2-add-auth` |
| `fix/3-fix-login` | `../endless8-fix-3-fix-login` |

### Commands

```bash
# 既存ブランチのワークツリー作成
git worktree add ../endless8-feat-2-add-auth feat/2-add-auth

# 新規ブランチとワークツリーを同時作成
git worktree add -b feat/2-add-auth ../endless8-feat-2-add-auth

# ワークツリーの一覧
git worktree list

# ワークツリーの削除
git worktree remove ../endless8-feat-2-add-auth
```
