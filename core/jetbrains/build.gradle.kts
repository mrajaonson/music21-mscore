plugins {
    id("buildsrc.convention.kotlin-jvm")
    id("org.jetbrains.intellij.platform") version "2.5.0"
}

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

dependencies {
    intellijPlatform {
        intellijIdeaCommunity("2024.3")
    }
}

intellijPlatform {
    pluginConfiguration {
        id = "org.solfadoc.jetbrains"
        name = "Solfadoc"
        version = "0.1.0"
        description = "Syntax highlighting for solfadoc notation files"
        vendor {
            name = "solfadoc"
        }
    }
}
