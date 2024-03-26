#!/bin/sh

script_path=$(readlink -f "$0")
script_bin=$(dirname "${script_path}")
script_name=$(basename "${script_path}")

if [ "$#" -lt 2 ] || [ "$#" -gt 4 ]; then
	echo "usage: ${script_name} SCRIPT ALGORITHM [CONSTRAINTS]" >&2
	exit 1
fi

script="$1"
algorithm="$2"
constraints="${3:-true}"

TPM_DB_URL=${TPM_DB_URL:-postgresql://${USER}@/tpm}

cat "${script_bin}/${script}" \
	| sed -e "s/%%PERF%%/$algorithm/g" \
	| sed -e "s/%%CONSTRAINTS%%/$constraints/" \
	| psql -d "$TPM_DB_URL" -1
