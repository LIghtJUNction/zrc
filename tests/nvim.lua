local root = vim.env.ZRC_TEST_ROOT
local init = root .. "/profiles/ink/files/.config/nvim"
for _, file in ipairs(vim.fn.glob(init .. "/**/*.lua", false, true)) do
  assert(loadfile(file), "Lua syntax: " .. file)
end
assert(vim.g.colors_name == "zrc-ink")
assert(vim.api.nvim_get_hl(0, { name = "Normal" }).bg == tonumber("161412", 16))
assert(not package.loaded["zrc.lsp"], "LSP must remain lazy before opening a supported file")
local context = require("zrc.context").collect()
assert(context.schema == "zrc.context.v1" and context.contents == nil)
local selected
require("zrc.picker").open({ { label = "alpha", value = 1 }, { label = "beta", value = 2 } },
  "Test picker", function(item) selected = item.value end)
local input = vim.api.nvim_get_current_buf()
vim.api.nvim_buf_set_lines(input, 0, -1, false, { "  › beta" })
vim.api.nvim_exec_autocmds("TextChangedI", { buffer = input })
assert(vim.wait(150, function()
  for _, win in ipairs(vim.api.nvim_list_wins()) do
    local b = vim.api.nvim_win_get_buf(win)
    if b ~= input and vim.bo[b].buftype == "nofile" then
      local content = table.concat(vim.api.nvim_buf_get_lines(b, 0, -1, false), "\n")
      if content:find("beta") and not content:find("alpha") then return true end
    end
  end
end, 10), "picker did not filter")
for _, mapping in ipairs(vim.api.nvim_buf_get_keymap(input, "i")) do
  if mapping.lhs == "<CR>" then mapping.callback(); break end
end
assert(vim.wait(100, function() return selected == 2 end, 10), "picker did not select original value")
assert(#vim.api.nvim_list_wins() == 1, "picker leaked a window")
require("zrc.welcome").open()
local welcome = vim.api.nvim_get_current_buf()
assert(table.concat(vim.api.nvim_buf_get_lines(welcome, 0, -1, false), "\n"):find("oh my ztty"))
require("zrc.picker").open({ { label = "cancel" } }, "Test", function() end)
assert(not vim.wo[vim.api.nvim_list_wins()[1]].number, "dashboard options changed on picker entry")
input = vim.api.nvim_get_current_buf()
for _, mapping in ipairs(vim.api.nvim_buf_get_keymap(input, "i")) do
  if mapping.lhs == "<Esc>" then mapping.callback(); break end
end
vim.cmd.enew()
local file = vim.env.ZRC_TEST_LARGE_FILE
vim.cmd.edit(vim.fn.fnameescape(file))
assert(vim.b.zrc_large_file == true, "large file mode missing")
assert(vim.bo.syntax == "" and not vim.bo.undofile, "large file work was not bounded")
-- LSP launches only a matching installed executable at a recognized project root.
local old_exec, old_start, old_root = vim.fn.executable, vim.lsp.start, vim.fs.root
local captured
vim.fn.executable = function(name) return name:find("/mason/bin/rust%-analyzer$") and 1 or 0 end
vim.lsp.start = function(config) captured = config; return 1 end
vim.fs.root = function() return "/test/project" end
vim.b.zrc_large_file = false
vim.bo.filetype = "rust"
require("zrc.lsp").attach(0)
assert(captured and captured.cmd[1]:find("/mason/bin/rust%-analyzer$"), "Mason fallback not reused")
captured = nil
vim.b.zrc_large_file = true
require("zrc.lsp").attach(0)
assert(captured == nil, "large file started LSP")
vim.fn.executable, vim.lsp.start, vim.fs.root = old_exec, old_start, old_root
print("PASS: Lua, palette, context, lazy LSP, picker, welcome, large file, Mason")
vim.cmd("qa!")
