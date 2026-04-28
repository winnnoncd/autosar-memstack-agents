/**
 * get_parameter.groovy
 * Read a single AUTOSAR ECUC parameter value by path.
 * Template variable: $PARAM_PATH
 *
 * Output: JSON { "param_path": "...", "value": "...", "type": "..." }
 */
import groovy.json.JsonOutput

def paramPath = "$PARAM_PATH"

try {
    def container = daVinci.project.getEcucContainer(paramPath)
    if (container == null) {
        // Try as a parameter directly
        def param = daVinci.project.getEcucParameterValue(paramPath)
        if (param == null) {
            println JsonOutput.toJson([
                status: "error",
                param_path: paramPath,
                message: "Parameter not found"
            ])
            return
        }
        println JsonOutput.toJson([
            status: "ok",
            param_path: paramPath,
            value: param.getValue()?.toString() ?: "",
            type: param.getDefinition()?.getClass()?.getSimpleName() ?: "unknown"
        ])
    } else {
        // It's a container — list its parameters
        def params = [:]
        container.getParameterValues().each { pv ->
            params[pv.getDefinition().getShortName()] = pv.getValue()?.toString() ?: ""
        }
        println JsonOutput.toJson([
            status: "ok",
            param_path: paramPath,
            container: container.getShortName(),
            parameters: params
        ])
    }
} catch (Exception e) {
    println JsonOutput.toJson([
        status: "error",
        param_path: paramPath,
        message: e.getMessage()
    ])
}
