local M = {}
-- One native floating picker, no process or network activity while filtering.
function M.open(items, title, accept)
  if #items == 0 then vim.notify("No matching items", vim.log.levels.INFO); return end
  if vim.o.columns < 30 or vim.o.lines < 12 then
    vim.ui.select(items, { prompt = title, format_item = function(item) return item.label end }, function(item)
      if item then accept(item) end
    end)
    return
  end
  local width = math.min(78, vim.o.columns - 8)
  local height = math.min(13, vim.o.lines - 8)
  local row = math.max(1, math.floor((vim.o.lines - height - 2) / 2))
  local col = math.floor((vim.o.columns - width) / 2)
  local original = vim.api.nvim_get_current_win()
  local input, list = vim.api.nvim_create_buf(false, true), vim.api.nvim_create_buf(false, true)
  vim.bo[input].buftype, vim.bo[input].bufhidden = "prompt", "wipe"
  vim.bo[list].buftype, vim.bo[list].bufhidden = "nofile", "wipe"
  local input_win = vim.api.nvim_open_win(input, true, {
    relative = "editor", row = row, col = col, width = width, height = 1, style = "minimal",
  })
  local list_win = vim.api.nvim_open_win(list, false, {
    relative = "editor", row = row + 1, col = col, width = width, height = height, style = "minimal", focusable = false,
  })
  vim.wo[input_win].winhighlight, vim.wo[list_win].winhighlight = "Normal:NormalFloat", "Normal:NormalFloat"
  local ns, selected, closed, generation = vim.api.nvim_create_namespace("ZrcPicker"), 1, false, 0
  local labels, by_label = {}, {}
  for i, item in ipairs(items) do
    local label = item.label:gsub("[%c]", " ")
    -- Preserve exact source values separately from their single-line display.
    labels[i] = string.format("%s  %s", label, "")
    by_label[labels[i]] = item
  end
  local filtered = labels
  local function close()
    if closed then return end
    closed = true
    vim.cmd.stopinsert()
    for _, win in ipairs({ list_win, input_win }) do
      if vim.api.nvim_win_is_valid(win) then vim.api.nvim_win_close(win, true) end
    end
    if vim.api.nvim_win_is_valid(original) then vim.api.nvim_set_current_win(original) end
  end
  local function draw()
    if closed or not vim.api.nvim_buf_is_valid(list) then return end
    local rows = { "  " .. title .. "   ·   " .. #filtered .. " results", "" }
    local start = math.max(1, selected - (height - 4))
    for i = start, math.min(#filtered, start + height - 3) do
      local label = vim.fn.strcharpart(filtered[i], 0, width - 6)
      rows[#rows + 1] = (i == selected and "  › " or "    ") .. label
    end
    while #rows < height do rows[#rows + 1] = "" end
    vim.api.nvim_buf_set_lines(list, 0, -1, false, rows)
    vim.api.nvim_buf_clear_namespace(list, ns, 0, -1)
    vim.api.nvim_buf_set_extmark(list, ns, 0, 0, { end_col = #rows[1], hl_group = "ZrcQuiet" })
    if #filtered > 0 then
      local line = selected - start + 2
      vim.api.nvim_buf_set_extmark(list, ns, line, 0, { end_col = #rows[line + 1], hl_group = "ZrcPickerActive" })
    end
  end
  local function choose()
    local item = by_label[filtered[selected] or ""]
    close()
    if item then vim.schedule(function() accept(item) end) end
  end
  local prompt = "  › "
  vim.fn.prompt_setprompt(input, prompt)
  vim.fn.prompt_setcallback(input, choose)
  local function move(delta)
    if #filtered > 0 then selected = ((selected - 1 + delta) % #filtered) + 1; draw() end
  end
  for _, mode in ipairs({ "i", "n" }) do
    vim.keymap.set(mode, "<Esc>", close, { buffer = input })
    vim.keymap.set(mode, "<C-c>", close, { buffer = input })
    vim.keymap.set(mode, "<CR>", choose, { buffer = input })
    for _, key in ipairs({ "<C-n>", "<Down>" }) do
      vim.keymap.set(mode, key, function() move(1) end, { buffer = input })
    end
    for _, key in ipairs({ "<C-p>", "<Up>" }) do
      vim.keymap.set(mode, key, function() move(-1) end, { buffer = input })
    end
  end
  vim.api.nvim_create_autocmd({ "TextChangedI", "TextChanged" }, {
    buffer = input, callback = function()
      generation = generation + 1
      local mine = generation
      vim.defer_fn(function()
        if closed or mine ~= generation then return end
        local line = vim.api.nvim_buf_get_lines(input, 0, 1, false)[1] or ""
        local query = line:sub(#prompt + 1)
        filtered = query == "" and labels or vim.fn.matchfuzzy(labels, query)
        selected = 1
        draw()
      end, 30)
    end,
  })
  vim.api.nvim_create_autocmd("WinClosed", {
    pattern = tostring(input_win), once = true, callback = function() vim.schedule(close) end,
  })
  draw()
  vim.cmd.startinsert()
end
return M
