#!/bin/bash

script_path=$(readlink -f "$0")
script_bin=$(dirname "${script_path}")
script_name=$(basename "${script_path}")

TPM_DB_URL=${TPM_DB_URL:-postgresql://${USER}@/tpm}

for algorithm in $(psql -d "$TPM_DB_URL" -Atq -c "select name from algorithm"); do
	echo -e "\e[96m* $algorithm\e[0m"
	time "${script_bin}/query.sh" "$algorithm"
done
