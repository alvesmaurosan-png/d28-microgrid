"""REV05.3: invariantes auditáveis; nenhuma inferência de homologação ou vazamento."""
from __future__ import annotations
import csv
import hashlib
import math
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_r2_inputs(*, production_nm3, substrate_t_per_day, digester_capacity_m3,
                       gasometer_capacity_nm3, chp_capacity_kw, electrical_efficiency,
                       fuel_lhv_kwh_per_nm3, dt_hours, physical_evidence):
    """Verifica identidade produção/substrato, TRH/volume e autonomia, sem inventar parâmetros."""
    if not isinstance(physical_evidence, dict):
        raise ValueError('R2: evidência física de substrato, TRH e autonomia obrigatória')
    names=('biogas_yield_nm3_per_t','substrate_density_t_per_m3',
           'hydraulic_retention_days','usable_volume_fraction','gasometer_autonomy_hours')
    try:
        v={k:float(physical_evidence[k]) for k in names}
        inputs=[float(x) for x in (substrate_t_per_day,digester_capacity_m3,
            gasometer_capacity_nm3,chp_capacity_kw,electrical_efficiency,
            fuel_lhv_kwh_per_nm3,dt_hours)]
    except (KeyError,ValueError,TypeError) as exc:
        raise ValueError('R2: evidência física incompleta ou não numérica') from exc
    if any(not math.isfinite(x) or x<=0 for x in [*v.values(),*inputs]):
        raise ValueError('R2: valores físicos inválidos')
    if v['usable_volume_fraction']>1 or inputs[4]>1:
        raise ValueError('R2: fração/eficiência superior a 1')
    substrate,digester,gasometer,chp,eta,lhv,dt=inputs
    expected=substrate*v['biogas_yield_nm3_per_t']*dt/24
    if not production_nm3 or any(not math.isfinite(float(p)) or
       not math.isclose(float(p),expected,rel_tol=1e-8,abs_tol=1e-8)
       for p in production_nm3):
        raise ValueError('R2: produção não corresponde a substrato/rendimento/Δt')
    minimum=substrate/v['substrate_density_t_per_m3']*v['hydraulic_retention_days']/v['usable_volume_fraction']
    if digester+1e-8<minimum:
        raise ValueError('R2: volume geométrico inferior ao mínimo pelo TRH')
    gas_min=chp/(eta*lhv)*v['gasometer_autonomy_hours']
    if gasometer+1e-8<gas_min:
        raise ValueError('R2: gasômetro inferior à autonomia nominal documentada')
    return {'production_nm3_interval_expected':expected,'digester_minimum_m3':minimum,
            'gasometer_minimum_nm3':gas_min,'scientific_approval':False}


def verify_rev09_charging_boundary(csv_path, generator_path):
    """Evidência de semântica do gerador, NÃO prova da genealogia do CSV gerado."""
    src=Path(generator_path).read_text(encoding='utf-8-sig')
    tokens=("'base_load':'not added; AC is charging-only'", "'power_ac_kw'", "'energy_ac_kwh'")
    if not all(t in src for t in tokens):
        raise ValueError('REV09: gerador não documenta fronteira charging-only')
    with Path(csv_path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not {'power_ac_kw','power_dc_kw','energy_ac_kwh','energy_dc_kwh'}.issubset(reader.fieldnames or []):
            raise ValueError('REV09: esquema AC/DC não identificado')
        n=0
        for row in reader:
            p=float(row['power_ac_kw']); e=float(row['energy_ac_kwh'])
            if not (math.isfinite(p) and math.isfinite(e) and p>=0 and e>=0):
                raise ValueError('REV09: demanda inválida')
            if not math.isclose(e,p*.25,abs_tol=1e-3):
                raise ValueError('REV09: energia e potência inconsistentes')
            n+=1
    if not n: raise ValueError('REV09: CSV vazio')
    return {'source_csv_sha256':sha256(csv_path),'generator_sha256':sha256(generator_path),
            'rows':n,'generator_declares_charging_only':True,
            'csv_lineage_to_generator':'NOT_DEMONSTRATED_BY_HASH_OR_BUILD_MANIFEST',
            'auxiliary_exclusion_status':'SUPPORTED_BY_GENERATOR_SEMANTICS_NOT_PROVEN_FOR_FILE',
            'scientific_approval':False}
