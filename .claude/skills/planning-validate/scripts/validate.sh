#!/usr/bin/env bash
#
# validate.sh - Planning artifacts validation script
#
# Validates spec.md, plan.md, data-model.md, and contracts/ for quality,
# completeness, and consistency.
#

set -euo pipefail

# ============================================================================
# EMBEDDED UTILITIES - DO NOT EDIT (regenerate with scripts/build.sh)
# ============================================================================

# --- path-resolver.sh ---
#
# path-resolver.sh - Shared path resolution utilities for speckit-gates skills
#
# Usage:
#   source path-resolver.sh
#   resolve_paths  # Sets FEATURE_DIR, SPEC_FILE, PLAN_FILE, etc.
#


# Colors for output (using COLOR_* naming convention)
readonly COLOR_RED='\033[0;31m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_NC='\033[0m' # No Color

# Find the repository root by looking for .git or .specify
find_repo_root() {
    local dir="$PWD"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.git" ]] || [[ -d "$dir/.specify" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# Resolve all paths using check-prerequisites.sh
resolve_paths() {
    local repo_root
    repo_root="$(find_repo_root)" || {
        echo -e "${COLOR_RED}Error: Could not find repository root${COLOR_NC}" >&2
        return 1
    }

    local prereq_script="$repo_root/.specify/scripts/bash/check-prerequisites.sh"

    if [[ ! -f "$prereq_script" ]]; then
        echo -e "${COLOR_RED}Error: check-prerequisites.sh not found at $prereq_script${COLOR_NC}" >&2
        return 1
    fi

    # Run check-prerequisites.sh --json and parse output
    local json_output
    json_output=$("$prereq_script" --json 2>/dev/null) || {
        echo -e "${COLOR_RED}Error: Failed to run check-prerequisites.sh${COLOR_NC}" >&2
        return 1
    }

    # Extract FEATURE_DIR from JSON
    FEATURE_DIR=$(echo "$json_output" | grep -o '"FEATURE_DIR":"[^"]*"' | cut -d'"' -f4)

    if [[ -z "$FEATURE_DIR" ]]; then
        echo -e "${COLOR_RED}Error: Could not determine FEATURE_DIR${COLOR_NC}" >&2
        return 1
    fi

    # Set standard paths
    REPO_ROOT="$repo_root"
    SPEC_FILE="$FEATURE_DIR/spec.md"
    PLAN_FILE="$FEATURE_DIR/plan.md"
    TASKS_FILE="$FEATURE_DIR/tasks.md"
    DATA_MODEL_FILE="$FEATURE_DIR/data-model.md"
    RESEARCH_FILE="$FEATURE_DIR/research.md"
    QUICKSTART_FILE="$FEATURE_DIR/quickstart.md"
    CONTRACTS_DIR="$FEATURE_DIR/contracts"
    CONSTITUTION_FILE="$repo_root/constitution.md"

    # Export for subshells
    export REPO_ROOT FEATURE_DIR SPEC_FILE PLAN_FILE TASKS_FILE
    export DATA_MODEL_FILE RESEARCH_FILE QUICKSTART_FILE CONTRACTS_DIR
    export CONSTITUTION_FILE

    return 0
}

# Check if a required file exists
require_file() {
    local file="$1"
    local name="${2:-$file}"

    if [[ ! -f "$file" ]]; then
        echo -e "${COLOR_RED}Error: Required file missing: $name${COLOR_NC}" >&2
        echo "Path: $file" >&2
        return 1
    fi
    return 0
}

# Check if an optional file exists (returns success either way)
check_optional_file() {
    local file="$1"
    [[ -f "$file" ]]
}

# Get the feature branch name from FEATURE_DIR
get_feature_branch() {
    if [[ -n "${FEATURE_DIR:-}" ]]; then
        basename "$FEATURE_DIR"
    else
        echo "unknown"
    fi
}

# Get current timestamp in ISO 8601 format
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# --- output-format.sh ---
#
# output-format.sh - Shared output formatting utilities for speckit-gates skills
#
# Usage:
#   source output-format.sh
#   print_status GREEN "All checks passed"
#

# Colors for terminal output
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_GRAY='\033[0;90m'
readonly COLOR_BOLD='\033[1m'

# Status emoji
readonly STATUS_GREEN="GREEN"
readonly STATUS_YELLOW="YELLOW"
readonly STATUS_RED="RED"

# Print a header section
print_header() {
    local skill_name="$1"
    local feature_branch="$2"
    local status="$3"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local status_display
    case "$status" in
        GREEN)  status_display="GREEN" ;;
        YELLOW) status_display="YELLOW" ;;
        RED)    status_display="RED" ;;
        *)      status_display="$status" ;;
    esac

    echo "## Quality Assessment: $skill_name"
    echo ""
    echo "**Status**: $status_display"
    echo "**Branch**: $feature_branch"
    echo "**Timestamp**: $timestamp"
    echo ""
}

# Print a section title
print_section() {
    local title="$1"
    echo "### $title"
    echo ""
}

# Print a finding entry
print_finding() {
    local severity="$1"
    local artifact="$2"
    local message="$3"

    local severity_display
    case "$severity" in
        error)   severity_display="error" ;;
        warning) severity_display="warning" ;;
        info)    severity_display="info" ;;
        *)       severity_display="$severity" ;;
    esac

    echo "| $severity_display | $artifact | $message |"
}

# Print findings table header
print_findings_header() {
    echo "| Severity | Artifact | Message |"
    echo "|----------|----------|---------|"
}

# Print a blocker entry
print_blocker() {
    local id="$1"
    local description="$2"
    local action="$3"

    echo "- **$id**: $description"
    echo "  - Suggested action: $action"
}

# Print a recommendation
print_recommendation() {
    local message="$1"
    echo "- $message"
}

# Print a check item (for release-check)
print_check_item() {
    local status="$1"
    local name="$2"
    local details="${3:-}"

    local icon
    case "$status" in
        pass) icon="[PASS]" ;;
        fail) icon="[FAIL]" ;;
        skip) icon="[SKIP]" ;;
        *)    icon="[ ? ]" ;;
    esac

    if [[ -n "$details" ]]; then
        echo "| $icon | $name | $details |"
    else
        echo "| $icon | $name | |"
    fi
}

# Print check items table header
print_check_table_header() {
    echo "| Status | Check | Details |"
    echo "|--------|-------|---------|"
}

# Print a progress bar (for progress-report)
print_progress_bar() {
    local completed="$1"
    local total="$2"
    local width="${3:-20}"

    if [[ "$total" -eq 0 ]]; then
        echo "[--------------------] 0%"
        return
    fi

    local percentage=$((completed * 100 / total))
    local filled=$((completed * width / total))
    local empty=$((width - filled))

    local bar=""
    for ((i=0; i<filled; i++)); do bar+="#"; done
    for ((i=0; i<empty; i++)); do bar+="-"; done

    echo "[$bar] $percentage% ($completed/$total)"
}

# Print a summary line
print_summary() {
    local label="$1"
    local value="$2"
    echo "**$label**: $value"
}

# Print coverage metrics
print_coverage() {
    local label="$1"
    local implemented="$2"
    local total="$3"

    if [[ "$total" -eq 0 ]]; then
        echo "- **$label**: N/A (no items)"
        return
    fi

    local percentage=$((implemented * 100 / total))
    echo "- **$label**: $implemented/$total ($percentage%)"
}

# Print a table row
print_table_row() {
    local columns=("$@")
    local row="|"
    for col in "${columns[@]}"; do
        row+=" $col |"
    done
    echo "$row"
}

# Print an error message to stderr
print_error() {
    local message="$1"
    echo -e "${COLOR_RED}Error: $message${COLOR_NC}" >&2
}

# Print a warning message to stderr
print_warning() {
    local message="$1"
    echo -e "${COLOR_YELLOW}Warning: $message${COLOR_NC}" >&2
}

# Print an info message
print_info() {
    local message="$1"
    echo -e "${COLOR_BLUE}Info: $message${COLOR_NC}"
}

# --- error-handler.sh ---
#
# error-handler.sh - Shared error handling utilities for speckit-gates skills
#
# Exit Codes:
#   0 - Success (GREEN status for validation skills)
#   1 - Warnings present (YELLOW status) or partial success
#   2 - Errors present (RED status) or low fulfillment
#   3 - Fatal error (missing required files, unexpected errors)
#

# Exit codes as constants
readonly EXIT_SUCCESS=0
readonly EXIT_WARNING=1
readonly EXIT_ERROR=2
readonly EXIT_FATAL=3

# Global error tracking
declare -g ERROR_COUNT=0
declare -g WARNING_COUNT=0
declare -g ERRORS=()
declare -g WARNINGS=()

# Reset error state
reset_errors() {
    ERROR_COUNT=0
    WARNING_COUNT=0
    ERRORS=()
    WARNINGS=()
}

# Record an error
record_error() {
    local message="$1"
    ERRORS+=("$message")
    ((ERROR_COUNT++)) || true
}

# Record a warning
record_warning() {
    local message="$1"
    WARNINGS+=("$message")
    ((WARNING_COUNT++)) || true
}

# Get error count
get_error_count() {
    echo "$ERROR_COUNT"
}

# Get warning count
get_warning_count() {
    echo "$WARNING_COUNT"
}

# Determine exit code based on error/warning counts
determine_exit_code() {
    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        echo "$EXIT_ERROR"
    elif [[ "$WARNING_COUNT" -gt 0 ]]; then
        echo "$EXIT_WARNING"
    else
        echo "$EXIT_SUCCESS"
    fi
}

# Determine status based on error/warning counts
determine_status() {
    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        echo "RED"
    elif [[ "$WARNING_COUNT" -gt 0 ]]; then
        echo "YELLOW"
    else
        echo "GREEN"
    fi
}

# Exit with error for missing required file
exit_missing_file() {
    local file="$1"
    local name="${2:-$file}"

    echo ""
    echo "## Error: Required File Missing"
    echo ""
    echo "**File**: $name"
    echo "**Path**: $file"
    echo ""
    echo "### Suggested Actions"
    echo ""
    echo "1. Ensure you have run the prerequisite spec kit commands"
    echo "2. Check that you are in the correct feature directory"
    echo "3. Verify the file exists at the expected path"
    echo ""

    exit "$EXIT_FATAL"
}

# Exit with error for unexpected error
exit_unexpected_error() {
    local message="$1"
    local details="${2:-}"

    echo ""
    echo "## Error: Unexpected Error"
    echo ""
    echo "**Message**: $message"
    if [[ -n "$details" ]]; then
        echo "**Details**: $details"
    fi
    echo ""
    echo "### Suggested Actions"
    echo ""
    echo "1. Check the error message for hints"
    echo "2. Verify your environment is correctly configured"
    echo "3. Report the issue if the problem persists"
    echo ""

    exit "$EXIT_FATAL"
}

# Print all recorded errors
print_errors() {
    if [[ "${#ERRORS[@]}" -eq 0 ]]; then
        return
    fi

    echo "### Errors"
    echo ""
    for error in "${ERRORS[@]}"; do
        echo "- $error"
    done
    echo ""
}

# Print all recorded warnings
print_warnings() {
    if [[ "${#WARNINGS[@]}" -eq 0 ]]; then
        return
    fi

    echo "### Warnings"
    echo ""
    for warning in "${WARNINGS[@]}"; do
        echo "- $warning"
    done
    echo ""
}

# Trap handler for unexpected script termination
handle_exit() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]] && [[ $exit_code -ne "$EXIT_WARNING" ]] && [[ $exit_code -ne "$EXIT_ERROR" ]]; then
        echo ""
        echo "## Skill Terminated Unexpectedly"
        echo ""
        echo "Exit code: $exit_code"
        echo ""
    fi
}

# Set up exit trap
setup_error_trap() {
    trap handle_exit EXIT
}

# Validate that a command exists
require_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        exit_unexpected_error "Required command not found: $cmd" "Please install $cmd and try again."
    fi
}

# ============================================================================
# END EMBEDDED UTILITIES
# ============================================================================




# Initialize
reset_errors
setup_error_trap

# Findings storage
declare -a FINDINGS=()
declare -a BLOCKERS=()
declare -a RECOMMENDATIONS=()

# Add a finding
add_finding() {
    local severity="$1"
    local artifact="$2"
    local message="$3"
    FINDINGS+=("$severity|$artifact|$message")

    if [[ "$severity" == "error" ]]; then
        record_error "$artifact: $message"
    elif [[ "$severity" == "warning" ]]; then
        record_warning "$artifact: $message"
    fi
}

# Add a blocker
add_blocker() {
    local id="$1"
    local description="$2"
    local action="$3"
    BLOCKERS+=("$id|$description|$action")
}

# Add a recommendation
add_recommendation() {
    local message="$1"
    RECOMMENDATIONS+=("$message")
}

# Check spec.md completeness (FR-002)
check_spec_completeness() {
    if [[ ! -f "$SPEC_FILE" ]]; then
        add_finding "error" "spec.md" "File not found"
        add_blocker "BLK-001" "spec.md is missing" "Run /speckit.specify to create specification"
        return
    fi

    local content
    content=$(cat "$SPEC_FILE")

    # Check for Summary/Overview section
    if ! echo "$content" | grep -qiE '^##?\s*(Summary|Overview)'; then
        add_finding "warning" "spec.md" "Missing Summary/Overview section"
        add_recommendation "Add a Summary section to spec.md"
    else
        add_finding "info" "spec.md" "Summary section present"
    fi

    # Check for User Stories section
    if ! echo "$content" | grep -qiE '^##?\s*User Stor(y|ies)'; then
        add_finding "error" "spec.md" "Missing User Stories section"
        add_blocker "BLK-002" "spec.md lacks User Stories" "Add User Stories section with at least one story"
    else
        # Check for at least one user story
        local story_count
        story_count=$(echo "$content" | grep -cE '^\s*-\s*(As a|As an)' || echo "0")
        if [[ "$story_count" -eq 0 ]]; then
            story_count=$(echo "$content" | grep -cE '^###\s+US[0-9]+' || echo "0")
        fi
        if [[ "$story_count" -eq 0 ]]; then
            add_finding "warning" "spec.md" "User Stories section exists but no stories found"
        else
            add_finding "info" "spec.md" "Found $story_count user stor(y|ies)"
        fi
    fi

    # Check for Functional Requirements section
    if ! echo "$content" | grep -qiE '^##?\s*Functional Requirements'; then
        add_finding "error" "spec.md" "Missing Functional Requirements section"
        add_blocker "BLK-003" "spec.md lacks Functional Requirements" "Add Functional Requirements section with FR-XXX items"
    else
        # Check for FR-XXX items
        local fr_count
        fr_count=$(echo "$content" | grep -cE 'FR-[0-9]+' || echo "0")
        if [[ "$fr_count" -eq 0 ]]; then
            add_finding "warning" "spec.md" "Functional Requirements section has no FR-XXX items"
        else
            add_finding "info" "spec.md" "Found $fr_count functional requirement references"
        fi
    fi

    # Check for Success Criteria section
    if ! echo "$content" | grep -qiE '^##?\s*Success Criteria'; then
        add_finding "warning" "spec.md" "Missing Success Criteria section"
        add_recommendation "Add Success Criteria section with measurable outcomes"
    else
        add_finding "info" "spec.md" "Success Criteria section present"
    fi
}

# Check plan.md executability (FR-003)
check_plan_executability() {
    if [[ ! -f "$PLAN_FILE" ]]; then
        add_finding "error" "plan.md" "File not found"
        add_blocker "BLK-004" "plan.md is missing" "Run /speckit.plan to create implementation plan"
        return
    fi

    local content
    content=$(cat "$PLAN_FILE")

    # Check for Technical Context section
    if ! echo "$content" | grep -qiE '^##?\s*Technical Context'; then
        add_finding "error" "plan.md" "Missing Technical Context section"
        add_blocker "BLK-005" "plan.md lacks Technical Context" "Ensure /speckit.plan completes successfully"
    else
        add_finding "info" "plan.md" "Technical Context section present"
    fi

    # Check for Project Structure section
    if ! echo "$content" | grep -qiE '^##?\s*Project Structure'; then
        add_finding "warning" "plan.md" "Missing Project Structure section"
        add_recommendation "Add Project Structure section showing file organization"
    else
        add_finding "info" "plan.md" "Project Structure section present"
    fi

    # Check for Constitution Check section
    if echo "$content" | grep -qiE '^##?\s*Constitution Check'; then
        add_finding "info" "plan.md" "Constitution Check section present"

        # Check for Gate Result
        if echo "$content" | grep -qE 'Gate Result.*PASS'; then
            add_finding "info" "plan.md" "Constitution gate passed"
        elif echo "$content" | grep -qE 'Gate Result.*FAIL'; then
            add_finding "error" "plan.md" "Constitution gate failed"
            add_blocker "BLK-006" "Constitution check failed in plan.md" "Review and fix constitution violations"
        fi
    fi
}

# Check data-model.md consistency (FR-004)
check_data_model_consistency() {
    if [[ ! -f "$DATA_MODEL_FILE" ]]; then
        add_finding "info" "data-model.md" "File not present (optional)"
        return
    fi

    local content
    content=$(cat "$DATA_MODEL_FILE")

    # Check for Entities section
    if ! echo "$content" | grep -qiE '^##?\s*Entities'; then
        add_finding "warning" "data-model.md" "Missing Entities section"
        add_recommendation "Add Entities section defining data structures"
    else
        add_finding "info" "data-model.md" "Entities section present"
    fi

    # Check for at least one entity (interface or type definition)
    local entity_count
    entity_count=$(echo "$content" | grep -cE '^###\s+[0-9]+\.\s+' || echo "0")
    if [[ "$entity_count" -eq 0 ]]; then
        entity_count=$(echo "$content" | grep -cE 'interface\s+\w+' || echo "0")
    fi

    if [[ "$entity_count" -eq 0 ]]; then
        add_finding "warning" "data-model.md" "No entities defined"
    else
        add_finding "info" "data-model.md" "Found $entity_count entit(y|ies) defined"
    fi
}

# Check contract coverage (FR-005)
check_contract_coverage() {
    if [[ ! -d "$CONTRACTS_DIR" ]]; then
        add_finding "info" "contracts/" "Directory not present (optional)"
        return
    fi

    local contract_count
    contract_count=$(find "$CONTRACTS_DIR" -name "*.md" -type f 2>/dev/null | wc -l)

    if [[ "$contract_count" -eq 0 ]]; then
        add_finding "warning" "contracts/" "Directory exists but no contract files found"
        add_recommendation "Add contract files to contracts/ directory"
    else
        add_finding "info" "contracts/" "Found $contract_count contract file(s)"
    fi
}

# Check constitution compliance (FR-006, FR-041)
check_constitution_compliance() {
    if [[ ! -f "$CONSTITUTION_FILE" ]]; then
        add_finding "info" "constitution.md" "File not present - skipping constitution checks"
        add_recommendation "Consider creating a constitution.md for project-wide standards"
        return
    fi

    add_finding "info" "constitution.md" "Constitution file present"

    # Check if plan.md references constitution principles
    if [[ -f "$PLAN_FILE" ]]; then
        local plan_content
        plan_content=$(cat "$PLAN_FILE")

        if echo "$plan_content" | grep -qiE 'constitution'; then
            add_finding "info" "plan.md" "References constitution principles"
        else
            add_finding "warning" "plan.md" "Does not explicitly reference constitution"
            add_recommendation "Ensure plan.md includes Constitution Check section"
        fi
    fi
}

# Output results
output_results() {
    local status
    status=$(determine_status)
    local feature_branch
    feature_branch=$(get_feature_branch)

    print_header "planning-validate" "$feature_branch" "$status"

    # Print findings
    if [[ ${#FINDINGS[@]} -gt 0 ]]; then
        print_section "Findings"
        print_findings_header
        for finding in "${FINDINGS[@]}"; do
            IFS='|' read -r severity artifact message <<< "$finding"
            print_finding "$severity" "$artifact" "$message"
        done
        echo ""
    fi

    # Print blockers
    if [[ ${#BLOCKERS[@]} -gt 0 ]]; then
        print_section "Blockers"
        for blocker in "${BLOCKERS[@]}"; do
            IFS='|' read -r id description action <<< "$blocker"
            print_blocker "$id" "$description" "$action"
        done
        echo ""
    else
        print_section "Blockers"
        echo "None"
        echo ""
    fi

    # Print recommendations
    if [[ ${#RECOMMENDATIONS[@]} -gt 0 ]]; then
        print_section "Recommendations"
        for rec in "${RECOMMENDATIONS[@]}"; do
            print_recommendation "$rec"
        done
        echo ""
    fi
}

# Main execution
main() {
    # Resolve paths
    if ! resolve_paths; then
        exit_unexpected_error "Failed to resolve paths" "Ensure you are in a spec kit project"
    fi

    # Check for required files (FR-038, FR-039)
    if [[ ! -f "$SPEC_FILE" ]] && [[ ! -f "$PLAN_FILE" ]]; then
        exit_missing_file "$SPEC_FILE" "spec.md (and plan.md also missing)"
    fi

    # Run all checks
    check_spec_completeness
    check_plan_executability
    check_data_model_consistency
    check_contract_coverage
    check_constitution_compliance

    # Output results
    output_results

    # Exit with appropriate code
    exit "$(determine_exit_code)"
}

main "$@"
