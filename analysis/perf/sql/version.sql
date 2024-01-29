create or replace function to_version(numeric) returns text as $$
	declare
		parts integer array;
		input alias for $1;
		mask bit(32);
		vh bit(32);
		vl bit(32);

	begin
		vh := (input / 4294967296)::bigint::bit(32);
		vl := (input % 4294967296)::bigint::bit(32);
		mask := (x'ffff')::bigint::bit(32);
		parts := '{0, 0, 0, 0}';

		parts[4] := (vl & mask)::integer;
		parts[2] := (vh & mask)::integer;
		mask := mask << 16;
		parts[3] := ((vl & mask) >> 16)::integer;
		parts[1] := ((vh & mask) >> 16)::integer;

		return CONCAT(parts[1]::text, '.', parts[2]::text, '.', parts[3]::text, '.', parts[4]::text);
	end;
$$ language plpgsql;
