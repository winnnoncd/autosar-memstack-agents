---
name: davinci-cli-reference
description: >
  DaVinci Configurator Classic CLI and PAI command reference.
  Quick-reference for all MCP tool capabilities.
---

# DaVinci Configurator CLI / PAI Reference

## CLI Commands (DaVinciCFG.exe)

```bash
# Open project
DaVinciCFG.exe --project <path>.dpa

# Import ARXML fragments (can specify multiple files)
DaVinciCFG.exe --project <path>.dpa --import file1.arxml file2.arxml

# Run validation, output report
DaVinciCFG.exe --project <path>.dpa --validate --report validation.xml

# Trigger code generation
DaVinciCFG.exe --project <path>.dpa --generate

# Export configuration as ARXML
DaVinciCFG.exe --project <path>.dpa --export output.arxml

# Synchronize ECU extract
DaVinciCFG.exe --project <path>.dpa --sync

# Execute PAI Groovy script
DaVinciCFG.exe --project <path>.dpa --script script.groovy
```

## Exit Codes
- 0: Success (or validation passed with 0 errors)
- 1: Validation completed with errors found
- 2+: Internal error / crash

## Platform Support
- Windows: all versions
- Linux: Generation 6+ (for CI server use)

## Startup Time
- Cold start: 15-30 seconds (large projects with many modules)
- PAI persistent session: eliminates per-call startup
- Recommendation: batch operations to minimize CLI invocations

## MCP Tools Mapping

| MCP Tool | CLI Command | PAI Alternative |
|---|---|---|
| davinci_open_project | --project | N/A (project always specified) |
| davinci_import_arxml | --import | N/A |
| davinci_validate | --validate --report | daVinci.project.validateAll() |
| davinci_generate | --generate | daVinci.project.generate() |
| davinci_export_arxml | --export | N/A |
| davinci_get_parameter | N/A (CLI can't read params) | getEcucParameterValue() |
| davinci_set_parameter | N/A (CLI can't write params) | param.setValue() |
| davinci_batch_set | N/A | Loop over setValue() in one script |

## PAI Groovy API (Option WF)
```groovy
// Open project (already loaded via --project)
def project = daVinci.project

// Read parameter
def param = project.getEcucParameterValue("/AUTOSAR/NvM/.../NvMNvBlockLength")
def value = param.getValue()

// Write parameter
param.setValue("128")

// Validate single container
def results = project.validate(container)

// Validate all
def allResults = project.validateAll()

// Access container by path
def container = project.getEcucContainer("/AUTOSAR/NvM/NvMBlockDescriptor_Odo")

// List all containers of a type
def blocks = moduleConfig.getContainersByDefinition("NvMBlockDescriptor")
```

## License Requirements
| Feature | License Needed |
|---|---|
| CLI: import, validate, generate | Standard DVP license |
| PAI: Groovy scripting | Option WF (Workflow) |
| Linux support | Generation 6+ license |
