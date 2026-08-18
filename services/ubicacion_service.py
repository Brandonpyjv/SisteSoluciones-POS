from database import get_many, get_one


def get_all_departamentos():
    return get_many("SELECT cod_departamento, nombre FROM departamentos ORDER BY nombre")


def get_municipios_by_departamento(cod_departamento: str):
    return get_many(
        "SELECT cod_municipio, nombre FROM municipios "
        "WHERE cod_departamento = %s ORDER BY nombre",
        (cod_departamento,)
    )


def get_municipio_by_id(cod_municipio: str):
    return get_one(
        "SELECT m.cod_municipio, m.nombre, m.cod_departamento, d.nombre AS nombre_departamento "
        "FROM municipios m JOIN departamentos d ON m.cod_departamento = d.cod_departamento "
        "WHERE m.cod_municipio = %s",
        (cod_municipio,)
    )
