/**
 * query_blocks.groovy
 * Query all block definitions for NvM, Fee, or Ea module.
 * Template variable: $MODULE (NvM, Fee, Ea)
 *
 * Output: JSON { "module", "blocks": [ { name, id, size, ... }, ... ] }
 */
import groovy.json.JsonOutput

def moduleName = "$MODULE"
def blocks = []

try {
    def moduleConfig = daVinci.project.getEcucModuleConfiguration(moduleName)
    if (moduleConfig == null) {
        println JsonOutput.toJson([
            status: "error",
            module: moduleName,
            message: "Module configuration not found"
        ])
        return
    }

    if (moduleName == "NvM") {
        moduleConfig.getContainersByDefinition("NvMBlockDescriptor").each { block ->
            def params = [:]
            block.getParameterValues().each { pv ->
                params[pv.getDefinition().getShortName()] = pv.getValue()?.toString() ?: ""
            }
            blocks.add([
                name: block.getShortName(),
                id: params.get("NvMNvBlockNum", ""),
                length: params.get("NvMNvBlockLength", ""),
                management_type: params.get("NvMBlockManagementType", ""),
                use_crc: params.get("NvMBlockUseCrc", "false"),
                crc_type: params.get("NvMBlockCrcType", ""),
                priority: params.get("NvMBlockJobPriority", ""),
                base_number: params.get("NvMNvBlockBaseNumber", "")
            ])
        }
    } else if (moduleName == "Fee") {
        moduleConfig.getContainersByDefinition("FeeBlockConfiguration").each { block ->
            def params = [:]
            block.getParameterValues().each { pv ->
                params[pv.getDefinition().getShortName()] = pv.getValue()?.toString() ?: ""
            }
            blocks.add([
                name: block.getShortName(),
                block_number: params.get("FeeBlockNumber", ""),
                block_size: params.get("FeeBlockSize", ""),
                immediate_data: params.get("FeeImmediateData", "false")
            ])
        }
    } else if (moduleName == "Ea") {
        moduleConfig.getContainersByDefinition("EaBlockConfiguration").each { block ->
            def params = [:]
            block.getParameterValues().each { pv ->
                params[pv.getDefinition().getShortName()] = pv.getValue()?.toString() ?: ""
            }
            blocks.add([
                name: block.getShortName(),
                block_number: params.get("EaBlockNumber", ""),
                block_size: params.get("EaBlockSize", ""),
                immediate_data: params.get("EaImmediateData", "false")
            ])
        }
    }

    println JsonOutput.toJson([
        status: "ok",
        module: moduleName,
        block_count: blocks.size(),
        blocks: blocks
    ])

} catch (Exception e) {
    println JsonOutput.toJson([
        status: "error",
        module: moduleName,
        message: e.getMessage()
    ])
}
