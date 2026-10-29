import conversacion
import errores_api
from curso_core import config as cfg


def test_usuario_crea_mensaje_de_usuario() -> None:
    mensaje = conversacion.usuario("hola")
    assert (mensaje.role, mensaje.content) == ("user", "hola")


def test_con_modelo_no_toca_la_configuracion_original() -> None:
    config = cfg.Config.model_validate(
        {
            "roles": {"remoto": {"provider": "p", "model": "original"}},
            "providers": {"p": {"tipo": "openai", "base_url": "http://p.test"}},
        }
    )
    copia = errores_api.con_modelo(config, "otro")
    assert copia.roles["remoto"].model == "otro"
    assert config.roles["remoto"].model == "original"
