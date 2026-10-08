from . import models, schemas


def turno_out(t: models.Turno) -> schemas.TurnoOut:
    return schemas.TurnoOut(
        id=t.id,
        usuario_id=t.usuario_id,
        profesor_id=t.profesor_id,
        usuario_nombre=t.usuario.nombre if t.usuario else "",
        profesor_nombre=t.profesor.nombre if t.profesor else "",
        fecha=t.fecha,
        rango_horario=t.rango_horario,
        estado=t.estado.value if t.estado else "pendiente",
        grupo_muscular=t.grupo_muscular,
        nota=t.nota,
    )
