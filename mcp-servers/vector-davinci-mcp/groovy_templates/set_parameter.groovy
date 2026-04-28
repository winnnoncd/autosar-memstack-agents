/**
 * set_parameter.groovy
 * Write a single AUTOSAR ECUC parameter value and mini-validate.
 * Template variables: $PARAM_PATH, $VALUE
 *
 * Output: JSON { "status", "param_path", "previous_value", "new_value", "validation" }
 */
import groovy.json.JsonOutput

def paramPath = "$PARAM_PATH"
def newValue = "$VALUE"

try {
    def param = daVinci.project.getEcucParameterValue(paramPath)
    if (param == null) {
        println JsonOutput.toJson([
            status: "error",
            param_path: paramPath,
            message: "Parameter not found at path"
        ])
        return
    }

    def previousValue = param.getValue()?.toString() ?: ""

    // Set the new value
    param.setValue(newValue)

    // Run mini-validation on the parent container
    def container = param.getParent()
    def validationResult = daVinci.project.validate(container)
    def errors = []
    validationResult.each { issue ->
        errors.add([
            severity: issue.getSeverity()?.toString() ?: "WARNING",
            message: issue.getMessage() ?: "",
            rule: issue.getRuleId() ?: ""
        ])
    }

    println JsonOutput.toJson([
        status: errors.isEmpty() ? "ok" : "ok_with_warnings",
        param_path: paramPath,
        previous_value: previousValue,
        new_value: newValue,
        validation_errors: errors
    ])

} catch (Exception e) {
    println JsonOutput.toJson([
        status: "error",
        param_path: paramPath,
        message: e.getMessage()
    ])
}
