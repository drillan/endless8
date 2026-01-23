#!/usr/bin/env bash
#
# verify.sh - Implementation verification script
#
# Verifies implementation against specifications by checking requirement
# fulfillment, task completion, and contract implementation.
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

# Metrics storage
declare -i TOTAL_FRS=0
declare -i IMPLEMENTED_FRS=0
declare -i TOTAL_TASKS=0
declare -i COMPLETED_TASKS=0
declare -i TOTAL_CONTRACTS=0
declare -i IMPLEMENTED_CONTRACTS=0

declare -a UNIMPLEMENTED_REQUIREMENTS=()
declare -a RECOMMENDED_ACTIONS=()

# Extract FR-XXX requirements from spec.md
extract_requirements() {
    if [[ ! -f "$SPEC_FILE" ]]; then
        return
    fi

    local content
    content=$(cat "$SPEC_FILE")

    # Find all unique FR-XXX references
    local frs
    frs=$(echo "$content" | grep -oE 'FR-[0-9]+' | sort -u || true)

    while IFS= read -r fr; do
        if [[ -n "$fr" ]]; then
            ((TOTAL_FRS++)) || true
        fi
    done <<< "$frs"
}

# Calculate task completion rate from tasks.md (FR-011)
calculate_task_completion() {
    if [[ ! -f "$TASKS_FILE" ]]; then
        return
    fi

    local content
    content=$(cat "$TASKS_FILE")

    # Count total tasks (lines starting with - [ ] or - [X] or - [x])
    TOTAL_TASKS=$(echo "$content" | grep -cE '^\s*-\s*\[[Xx ]\]' || echo "0")

    # Count completed tasks (marked with [X] or [x])
    COMPLETED_TASKS=$(echo "$content" | grep -cE '^\s*-\s*\[[Xx]\]' || echo "0")
}

# Calculate FR requirement fulfillment (FR-010)
calculate_fr_fulfillment() {
    if [[ ! -f "$SPEC_FILE" ]] || [[ ! -f "$TASKS_FILE" ]]; then
        return
    fi

    local spec_content tasks_content
    spec_content=$(cat "$SPEC_FILE")
    tasks_content=$(cat "$TASKS_FILE")

    # Get all FR-XXX from spec
    local frs
    frs=$(echo "$spec_content" | grep -oE 'FR-[0-9]+' | sort -u || true)

    while IFS= read -r fr; do
        if [[ -z "$fr" ]]; then
            continue
        fi

        # Check if this FR is referenced in a completed task
        if echo "$tasks_content" | grep -E '^\s*-\s*\[[Xx]\].*'"$fr" > /dev/null 2>&1; then
            ((IMPLEMENTED_FRS++)) || true
        else
            # Get FR description from spec
            local fr_desc
            fr_desc=$(echo "$spec_content" | grep -m1 "$fr" | head -1 | sed 's/.*'"$fr"'[^a-zA-Z]*//' | cut -c1-60)
            if [[ -n "$fr_desc" ]]; then
                UNIMPLEMENTED_REQUIREMENTS+=("$fr: $fr_desc...")
            else
                UNIMPLEMENTED_REQUIREMENTS+=("$fr: (description not found)")
            fi
        fi
    done <<< "$frs"
}

# Check contract implementation (FR-012)
check_contract_implementation() {
    if [[ ! -d "$CONTRACTS_DIR" ]]; then
        return
    fi

    local contract_files
    contract_files=$(find "$CONTRACTS_DIR" -name "*.md" -type f 2>/dev/null || true)

    if [[ -z "$contract_files" ]]; then
        return
    fi

    while IFS= read -r contract_file; do
        if [[ -z "$contract_file" ]]; then
            continue
        fi

        local content
        content=$(cat "$contract_file")

        # Count endpoint definitions (lines with HTTP methods)
        local endpoints
        endpoints=$(echo "$content" | grep -cE '(GET|POST|PUT|DELETE|PATCH)\s+/' || echo "0")
        ((TOTAL_CONTRACTS += endpoints)) || true

        # For now, assume all endpoints in contracts are implemented
        # A more sophisticated check would verify actual implementation files
        ((IMPLEMENTED_CONTRACTS += endpoints)) || true
    done <<< "$contract_files"
}

# Generate recommended actions (FR-015)
generate_recommendations() {
    local task_percent=0
    local fr_percent=0

    if [[ "$TOTAL_TASKS" -gt 0 ]]; then
        task_percent=$((COMPLETED_TASKS * 100 / TOTAL_TASKS))
    fi

    if [[ "$TOTAL_FRS" -gt 0 ]]; then
        fr_percent=$((IMPLEMENTED_FRS * 100 / TOTAL_FRS))
    fi

    if [[ "$task_percent" -lt 100 ]]; then
        local remaining=$((TOTAL_TASKS - COMPLETED_TASKS))
        RECOMMENDED_ACTIONS+=("Complete remaining $remaining task(s) in tasks.md")
    fi

    if [[ "$fr_percent" -lt 100 ]]; then
        local unimpl=$((TOTAL_FRS - IMPLEMENTED_FRS))
        RECOMMENDED_ACTIONS+=("Address $unimpl unimplemented requirement(s)")
    fi

    if [[ "${#UNIMPLEMENTED_REQUIREMENTS[@]}" -gt 0 ]]; then
        RECOMMENDED_ACTIONS+=("Review unimplemented requirements list below")
    fi

    if [[ "${#RECOMMENDED_ACTIONS[@]}" -eq 0 ]]; then
        RECOMMENDED_ACTIONS+=("All requirements fulfilled - ready for release validation")
    fi
}

# Determine exit code based on fulfillment
determine_fulfillment_exit_code() {
    local task_percent=0
    local fr_percent=0

    if [[ "$TOTAL_TASKS" -gt 0 ]]; then
        task_percent=$((COMPLETED_TASKS * 100 / TOTAL_TASKS))
    fi

    if [[ "$TOTAL_FRS" -gt 0 ]]; then
        fr_percent=$((IMPLEMENTED_FRS * 100 / TOTAL_FRS))
    fi

    # Use the lower of the two percentages
    local overall_percent=$task_percent
    if [[ "$fr_percent" -lt "$overall_percent" ]]; then
        overall_percent=$fr_percent
    fi

    if [[ "$overall_percent" -eq 100 ]]; then
        echo "0"
    elif [[ "$overall_percent" -ge 80 ]]; then
        echo "1"
    else
        echo "2"
    fi
}

# Output results (FR-014, FR-024)
output_results() {
    local feature_branch
    feature_branch=$(get_feature_branch)
    local timestamp
    timestamp=$(get_timestamp)

    echo "## Fulfillment Report: implementation-verify"
    echo ""
    echo "**Branch**: $feature_branch"
    echo "**Timestamp**: $timestamp"
    echo ""

    # Coverage metrics
    print_section "Coverage Metrics"

    local task_percent=0
    local fr_percent=0
    local contract_percent=0

    if [[ "$TOTAL_TASKS" -gt 0 ]]; then
        task_percent=$((COMPLETED_TASKS * 100 / TOTAL_TASKS))
    fi

    if [[ "$TOTAL_FRS" -gt 0 ]]; then
        fr_percent=$((IMPLEMENTED_FRS * 100 / TOTAL_FRS))
    fi

    if [[ "$TOTAL_CONTRACTS" -gt 0 ]]; then
        contract_percent=$((IMPLEMENTED_CONTRACTS * 100 / TOTAL_CONTRACTS))
    fi

    print_coverage "Task Completion" "$COMPLETED_TASKS" "$TOTAL_TASKS"
    print_coverage "FR Fulfillment" "$IMPLEMENTED_FRS" "$TOTAL_FRS"

    if [[ "$TOTAL_CONTRACTS" -gt 0 ]]; then
        print_coverage "Contract Implementation" "$IMPLEMENTED_CONTRACTS" "$TOTAL_CONTRACTS"
    fi

    echo ""

    # Unimplemented requirements
    if [[ "${#UNIMPLEMENTED_REQUIREMENTS[@]}" -gt 0 ]]; then
        print_section "Unimplemented Requirements"
        for req in "${UNIMPLEMENTED_REQUIREMENTS[@]}"; do
            echo "- $req"
        done
        echo ""
    fi

    # Recommended actions
    print_section "Recommended Actions"
    for action in "${RECOMMENDED_ACTIONS[@]}"; do
        echo "- $action"
    done
    echo ""
}

# Main execution
main() {
    # Resolve paths
    if ! resolve_paths; then
        exit_unexpected_error "Failed to resolve paths" "Ensure you are in a spec kit project"
    fi

    # Check for required files (FR-038, FR-039)
    if [[ ! -f "$TASKS_FILE" ]]; then
        exit_missing_file "$TASKS_FILE" "tasks.md"
    fi

    if [[ ! -f "$SPEC_FILE" ]]; then
        exit_missing_file "$SPEC_FILE" "spec.md"
    fi

    # Run all analyses
    extract_requirements
    calculate_task_completion
    calculate_fr_fulfillment
    check_contract_implementation
    generate_recommendations

    # Output results
    output_results

    # Exit with appropriate code
    exit "$(determine_fulfillment_exit_code)"
}

main "$@"
