/**
 * batch_set.groovy
 * Set multiple AUTOSAR ECUC parameters in one DVP session.
 * Avoids per-call startup cost (15-30s saved per call).
 * Template variable: $PARAMS_JSON — JSON object { path: value, ... }
 *
 * Output: JSON { "status", "set_count", "errors", "validation_errors" }
 */
import groovy.json.JsonOutput
import groovy.json.JsonSlurper

def paramsJson = '$PARAMS_JSON'
def slurper = new JsonSlurper()
def params = slurper.parseText(paramsJson)

def results = []
def setErrors = []
def setCount = 0

params.each { paramPath, newValue ->
    try {
        def param = daVinci.project.getEcucParameterValue(paramPath)
        if (param == null) {
            setErrors.add([
                param_path: paramPath,
                message: "Parameter not found"
            ])
            return
        }

        def previousValue = param.getValue()?.toString() ?: ""
        param.setValue(newValue.toString())
        setCount++

        results.add([
            param_path: paramPath,
            previous_value: previousValue,
            new_value: newValue.toString()
        ])
    } catch (Exception e) {
        setErrors.add([
            param_path: paramPath,
            message: e.getMessage()
        ])
    }
}

// Run full validation after all parameters are set
def validationErrors = []
try {
    def validationResult = daVinci.project.validateAll()
    validationResult.each { issue ->
        if (issue.getSeverity()?.toString() == "ERROR") {
            validationErrors.add([
                severity: "ERROR",
                module: issue.getModule() ?: "",
                message: issue.getMessage() ?: "",
                rule: issue.getRuleId() ?: ""
            ])
        }
    }
} catch (Exception e) {
    validationErrors.add([
        severity: "ERROR",
        message: "Validation failed: ${e.getMessage()}"
    ])
}

println JsonOutput.toJson([
    status: setErrors.isEmpty() && validationErrors.isEmpty() ? "ok" : "partial",
    set_count: setCount,
    total_requested: params.size(),
    results: results,
    set_errors: setErrors,
    validation_errors: validationErrors
])
