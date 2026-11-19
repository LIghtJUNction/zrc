-- zrc: native Neovim configuration; no downloads or plugin bootstrap.
local root = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":p:h")
vim.opt.runtimepath:prepend(root)
require("zrc").setup()
