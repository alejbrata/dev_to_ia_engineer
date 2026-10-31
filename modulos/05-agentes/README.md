# Módulo 5 — Agentes: código de las prácticas

El caso de todo el módulo es un agente de guardia sobre la plataforma de los módulos 2 a 4: recibe una alerta, investiga con herramientas (estado del servicio, logs, documentación) y decide si abre una incidencia, con qué severidad y con qué mitigación.

- `datos/escenarios.jsonl`: 14 escenarios (9 de desarrollo, 5 de prueba). Cada uno es una alerta y el estado simulado de la plataforma, con lo esperado anclado al corpus del módulo 3: la severidad sale de los criterios de `severidades.md` y la mitigación, del runbook. Incluye una falsa alarma, un pico pasajero y una instrucción inyectada en los logs.
- `plataforma.py`: la plataforma simulada. Escenarios, las cuatro herramientas (`buscar_documentacion`, `estado_servicio`, `buscar_logs`, `abrir_incidencia`), la validación de sus argumentos y `comprobar`, que juzga el estado final de la plataforma, no lo que dice el agente. `test_plataforma.py` comprueba el anclaje y la comprobación.
- `agente.py`: el bucle del agente sin framework, con límite de pasos y registro de cada paso (lección 03).
- `workflow.py`: la misma tarea como workflow fijo, con dos llamadas al modelo (lección 01).
- `medir_modelos.py`: el agente con cuatro modelos locales, para elegir el del módulo (lección 02).
- `medir_herramientas.py`: las herramientas de la versión 1 frente a las de la versión 2, mejor descritas (lección 02).
- `traza.py`: ejecuta el agente en un escenario y muestra su traza paso a paso.
- `workflow_frente_agente.py`: la misma tarea como workflow y como agente (lección 01).
- `bucle.py`: el bucle por dentro: tokens por paso, límite de pasos y razonamiento en cada paso (lección 03).
- `planificador.py` y `planificar.py`: el agente que escribe el plan como grafo de tareas, lo valida, lo ejecuta en orden topológico y replanifica; comparado con el workflow y el agente (lección 04). `test_planificador.py` prueba la validación y el orden.
- `grafo.py`: un motor de grafos de estado desde cero: estado tipado, aristas fijas y condicionales, límite de pasos, checkpoints en JSONL e interrupciones (lección 05). `test_grafo.py` lo prueba sin modelo.
- `grafo_guardia.py` y `grafos.py`: el agente de guardia como grafo, con aprobación humana antes de abrir la incidencia y reanudación tras una caída (lección 05). Con `--humano`, apruebas tú.
- `grafo_langgraph.py` y `con_langgraph.py`: los mismos nodos con LangGraph, comparado con el motor propio (lección 06).
- `memoria.py` y `memoria_y_contexto.py`: recortar el contexto del bucle y dar al agente memoria de escenarios ya cerrados (lección 07).
- `subagentes.py` y `delegar.py`: un orquestador que delega en subagentes con contexto aislado, frente al agente único (lección 08). `test_contexto.py` prueba el recorte y los permisos de los subagentes.
- `checkpoints/`: los checkpoints de los grafos. No se versiona.
- `resultados/`: resultados grabados caso a caso (`curso_core.evals.Informe`). Con `--grabadas`, las prácticas los reutilizan sin llamar al modelo.

Los prompts están en `prompts/agentes/`.
