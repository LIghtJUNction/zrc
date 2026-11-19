local M = {}
local servers = {
  rust = { name = "rust-analyzer", cmd = { "rust-analyzer" }, roots = { "Cargo.toml", ".git" } },
  c = { name = "clangd", cmd = { "clangd" }, roots = { "compile_commands.json", ".clangd", ".git" } },
  cpp = { name = "clangd", cmd = { "clangd" }, roots = { "compile_commands.json", ".clangd", ".git" } },
  go = { name = "gopls", cmd = { "gopls" }, roots = { "go.work", "go.mod", ".git" } },
  python = { name = "pyright", cmd = { "pyright-langserver", "--stdio" }, roots = { "pyproject.toml", "setup.py", ".git" } },
  lua = { name = "lua-language-server", cmd = { "lua-language-server" }, roots = { ".luarc.json", ".luarc.jsonc", ".git" } },
  sh = { name = "bash-language-server", cmd = { "bash-language-server", "start" }, roots = { ".git" } },
  javascript = { name = "typescript-language-server", cmd = { "typescript-language-server", "--stdio" }, roots = { "package.json", ".git" } },
  typescript = { name = "typescript-language-server", cmd = { "typescript-language-server", "--stdio" }, roots = { "tsconfig.json", "package.json", ".git" } },
}
servers.javascriptreact, servers.typescriptreact = servers.javascript, servers.typescript
function M.attach(buf)
  if vim.b[buf].zrc_large_file or vim.bo[buf].buftype ~= "" then return end
  local spec = servers[vim.bo[buf].filetype]
  if not spec then return end
  local command = vim.deepcopy(spec.cmd)
  if vim.fn.executable(command[1]) ~= 1 then
    local mason = vim.fn.stdpath("data") .. "/mason/bin/" .. command[1]
    if vim.fn.executable(mason) ~= 1 then return end
    command[1] = mason
  end
  local root = vim.fs.root(buf, spec.roots)
  if not root then return end -- a loose file must not index the user's home directory
  vim.lsp.start({
    name = spec.name, cmd = command, root_dir = root,
    on_attach = function(client, buffer)
      vim.bo[buffer].omnifunc = "v:lua.vim.lsp.omnifunc"
      if vim.lsp.completion then
        vim.lsp.completion.enable(true, client.id, buffer, { autotrigger = true })
      end
      local map = function(key, fn, desc)
        vim.keymap.set("n", key, fn, { buffer = buffer, desc = desc })
      end
      map("gd", vim.lsp.buf.definition, "Definition")
      map("gr", vim.lsp.buf.references, "References")
      map("K", vim.lsp.buf.hover, "Documentation")
    end,
  }, { bufnr = buf })
end
vim.diagnostic.config({
  virtual_text = false, severity_sort = true, update_in_insert = false,
  float = { border = "rounded", source = true },
  signs = { text = { [1] = "●", [2] = "●", [3] = "·", [4] = "·" } },
})
return M
