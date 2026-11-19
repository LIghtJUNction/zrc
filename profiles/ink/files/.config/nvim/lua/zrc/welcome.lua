local M = {}
function M.open()
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_set_current_buf(buf)
  vim.bo[buf].buftype, vim.bo[buf].bufhidden, vim.bo[buf].swapfile = "nofile", "wipe", false
  vim.bo[buf].filetype = "zrc-welcome"
  local win = vim.api.nvim_get_current_win()
  vim.wo[win].number, vim.wo[win].relativenumber, vim.wo[win].cursorline = false, false, false
  vim.wo[win].signcolumn = "no"
  local ns = vim.api.nvim_create_namespace("ZrcWelcome")
  local actions = {
    { "f", "Find a file", function() require("zrc.search").files() end },
    { "/", "Search your project", function() require("zrc.search").grep() end },
    { "r", "Recent files", function() require("zrc.search").recent() end },
    { "e", "New buffer", function() vim.cmd.enew(); vim.cmd.startinsert() end },
    { "?", "Keyboard shortcuts", function() require("zrc").help() end },
    { "q", "Quit", function() vim.cmd.quit() end },
  }
  local function draw()
    if not vim.api.nvim_buf_is_valid(buf) or not vim.api.nvim_win_is_valid(win) then return end
    local width, height = vim.api.nvim_win_get_width(win), vim.api.nvim_win_get_height(win)
    local left = math.max(2, math.floor((width - 42) / 2))
    local top = math.max(1, math.floor((height - 17) / 2))
    local pad, lines, marks = string.rep(" ", left), {}, {}
    for _ = 1, top do lines[#lines + 1] = "" end
    local function add(text, hl)
      lines[#lines + 1] = pad .. text
      if hl then marks[#marks + 1] = { #lines - 1, left, #lines[#lines], hl } end
    end
    add("oh my ztty", "ZrcTitle")
    add("A quiet place to build.", "Comment")
    add("")
    add("")
    for _, action in ipairs(actions) do add(string.format("%-5s%s", action[1], action[2]), "Normal") end
    add("")
    add("")
    add("zrc / ink", "ZrcQuiet")
    vim.bo[buf].modifiable = true
    vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
    vim.api.nvim_buf_clear_namespace(buf, ns, 0, -1)
    for _, mark in ipairs(marks) do
      vim.api.nvim_buf_set_extmark(buf, ns, mark[1], mark[2], { end_col = mark[3], hl_group = mark[4] })
    end
    for i = 1, #actions do
      vim.api.nvim_buf_set_extmark(buf, ns, top + 3 + i, left, { end_col = left + 1, hl_group = "ZrcAccent" })
    end
    vim.bo[buf].modifiable = false
    vim.api.nvim_win_set_cursor(win, { top + 5, left })
  end
  for _, action in ipairs(actions) do
    vim.keymap.set("n", action[1], action[3], { buffer = buf, silent = true, desc = action[2] })
  end
  draw()
  vim.api.nvim_create_autocmd("VimResized", { group = "Zrc", callback = draw })
  vim.api.nvim_create_autocmd("BufWinLeave", {
    buffer = buf, once = true, callback = function()
      if vim.api.nvim_win_is_valid(win) then
        vim.wo[win].number, vim.wo[win].relativenumber, vim.wo[win].cursorline = true, true, true
        vim.wo[win].signcolumn = "yes"
      end
    end,
  })
end
return M
