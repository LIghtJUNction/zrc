local M = {}
M.options = { large_file_bytes = 1024 * 1024, max_files = 4000, lsp = true }
M.keys = {
  { "Space f f", "Find file", function() require("zrc.search").files() end },
  { "Space f g", "Search text", function() require("zrc.search").grep() end },
  { "Space f r", "Recent files", function() require("zrc.search").recent() end },
  { "Space b b", "Buffers", function() require("zrc.search").buffers() end },
  { "Space e", "File explorer", function() vim.cmd.Explore() end },
  { "Space w", "Save", function() vim.cmd.write() end },
  { "Space c a", "Code actions", function() vim.lsp.buf.code_action() end },
  { "Space c r", "Rename symbol", function() vim.lsp.buf.rename() end },
  { "Space c f", "Format buffer", function() vim.lsp.buf.format({ async = true }) end },
  { "Space d", "Line diagnostics", function() vim.diagnostic.open_float() end },
  { "Space a c", "Local AI context", function() require("zrc.context").show() end },
  { "Space a s", "Connect ssmcp", function() require("zrc.context").connect() end },
  { "Space ?", "All shortcuts", function() M.help() end },
}
local mappings = { "<leader>ff", "<leader>fg", "<leader>fr", "<leader>bb", "<leader>e",
  "<leader>w", "<leader>ca", "<leader>cr", "<leader>cf", "<leader>d", "<leader>ac", "<leader>as", "<leader>?" }

function M.help()
  local items = {}
  for _, entry in ipairs(M.keys) do
    items[#items + 1] = { label = string.format("%-16s %s", entry[1], entry[2]), action = entry[3] }
  end
  require("zrc.picker").open(items, "Shortcuts", function(item) item.action() end)
end

function M.extend(extension)
  assert(type(extension) == "table" and type(extension.setup) == "function", "extension needs setup")
  if extension.event then
    vim.api.nvim_create_autocmd(extension.event, {
      group = M.group, pattern = extension.pattern, once = extension.once ~= false,
      callback = function(args)
        local ok, err = pcall(extension.setup, args)
        if not ok then vim.notify("zrc extension: " .. tostring(err), vim.log.levels.ERROR) end
      end,
    })
  else
    local ok, err = pcall(extension.setup)
    if not ok then vim.notify("zrc extension: " .. tostring(err), vim.log.levels.ERROR) end
  end
end

function M.setup()
  vim.g.mapleader, vim.g.maplocalleader = " ", " "
  M.group = vim.api.nvim_create_augroup("Zrc", { clear = true })
  local config = vim.env.XDG_CONFIG_HOME or (vim.env.HOME .. "/.config")
  local override = config .. "/zrc/nvim.lua"
  if vim.uv.fs_stat(override) then
    local ok, settings = pcall(dofile, override)
    if ok and type(settings) == "table" then M.options = vim.tbl_deep_extend("force", M.options, settings)
    elseif not ok then vim.notify("zrc config: " .. tostring(settings), vim.log.levels.ERROR) end
  end
  local o = vim.opt
  o.termguicolors = true
  o.number, o.relativenumber = true, true
  o.cursorline, o.wrap = true, false
  o.scrolloff, o.sidescrolloff = 6, 6
  o.signcolumn, o.laststatus = "yes", 3
  o.showmode, o.showcmd, o.ruler = false, false, false
  o.splitright, o.splitbelow = true, true
  o.mouse, o.ignorecase, o.smartcase = "a", true, true
  o.updatetime, o.timeoutlen = 250, 400
  o.completeopt, o.pumheight = { "menu", "menuone", "noselect" }, 10
  o.undofile, o.modeline = true, false
  o.expandtab, o.shiftwidth, o.tabstop = true, 2, 2
  o.synmaxcol = 240
  o.fillchars = { eob = " ", vert = " " }
  o.shortmess:append("I")
  vim.g.netrw_banner, vim.g.netrw_liststyle = 0, 3
  vim.g.netrw_winsize = 28
  vim.cmd.colorscheme("zrc-ink")
  require("zrc.statusline").setup()
  for i, entry in ipairs(M.keys) do
    vim.keymap.set("n", mappings[i], entry[3], { desc = entry[2], silent = true })
  end
  vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<cr>", { desc = "Clear search highlight" })
  vim.keymap.set("i", "<C-Space>", function()
    if #vim.lsp.get_clients({ bufnr = 0 }) > 0 then return "<C-x><C-o>" end
    return "<C-n>"
  end, { expr = true, desc = "Complete" })
  vim.api.nvim_create_user_command("ZrcKeys", M.help, {})
  vim.api.nvim_create_user_command("ZrcContext", function() require("zrc.context").show() end, {})
  vim.api.nvim_create_user_command("ZrcConnect", function() require("zrc.context").connect() end, {})
  vim.api.nvim_create_user_command("ZrcHealth", function()
    local present = {}
    for _, name in ipairs({ "rg", "ssmcp", "rust-analyzer", "clangd", "gopls", "pyright-langserver",
      "typescript-language-server", "lua-language-server" }) do
      present[#present + 1] = { label = string.format("%-28s %s", name,
        vim.fn.executable(name) == 1 and "available" or "optional · not installed") }
    end
    require("zrc.picker").open(present, "Health", function() end)
  end, {})
  vim.api.nvim_create_autocmd("BufReadPre", {
    group = M.group, callback = function(args)
      local size = vim.uv.fs_stat(vim.api.nvim_buf_get_name(args.buf))
      if size and size.size > M.options.large_file_bytes then
        vim.b[args.buf].zrc_large_file = true
        vim.bo[args.buf].undofile = false
      end
    end,
  })
  vim.api.nvim_create_autocmd({ "BufReadPost", "BufWinEnter" }, {
    group = M.group, callback = function(args)
      if vim.b[args.buf].zrc_large_file or vim.api.nvim_buf_line_count(args.buf) > 20000 then
        vim.b[args.buf].zrc_large_file = true
        vim.bo[args.buf].syntax = ""
        pcall(vim.treesitter.stop, args.buf)
      end
    end,
  })
  vim.api.nvim_create_autocmd("FileType", {
    group = M.group, callback = function(args)
      if vim.b[args.buf].zrc_large_file then vim.bo[args.buf].syntax = ""; return end
      if M.options.lsp and vim.bo[args.buf].buftype == "" then require("zrc.lsp").attach(args.buf) end
    end,
  })
  local stdin = false
  vim.api.nvim_create_autocmd("StdinReadPre", { group = M.group, callback = function() stdin = true end })
  vim.api.nvim_create_autocmd("VimEnter", {
    group = M.group, once = true, callback = function()
      if not stdin and vim.fn.argc() == 0 and vim.api.nvim_buf_get_name(0) == ""
          and vim.bo.buftype == "" and vim.api.nvim_buf_line_count(0) == 1
          and vim.api.nvim_buf_get_lines(0, 0, 1, false)[1] == "" then
        require("zrc.welcome").open()
      end
    end,
  })
  for _, extension in ipairs(M.options.extensions or {}) do M.extend(extension) end
end
return M
