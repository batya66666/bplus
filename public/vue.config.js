const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  // Добавьте эту строку, чтобы отключить блокирующую проверку:
  lintOnSave: false
})