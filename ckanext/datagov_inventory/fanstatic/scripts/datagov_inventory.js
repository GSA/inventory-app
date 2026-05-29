(function () {
  function cellText(row, index) {
    return row.children[index].textContent.trim().toLowerCase();
  }

  function updateHeaders(buttons, sortState) {
    buttons.forEach(function (button) {
      var th = button.closest('th');
      var indicator = '';
      if (Number(th.dataset.sortIndex) === sortState.index) {
        indicator = sortState.direction === 'asc' ? ' \u25B2' : ' \u25BC';
      }
      button.textContent = th.dataset.label + indicator;
    });
  }

  function sortTable(table, buttons, sortState, index) {
    if (sortState.index === index) {
      sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
    } else {
      sortState.index = index;
      sortState.direction = 'asc';
    }

    var tbody = table.querySelector('tbody');
    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
    rows.sort(function (left, right) {
      var leftText = cellText(left, index);
      var rightText = cellText(right, index);
      var comparison = leftText.localeCompare(rightText);
      return sortState.direction === 'asc' ? comparison : -comparison;
    });
    rows.forEach(function (row) {
      tbody.appendChild(row);
    });
    updateHeaders(buttons, sortState);
  }

  document.querySelectorAll('table[data-sortable-table]').forEach(function (table) {
    var sortState = { index: 0, direction: 'asc' };
    var buttons = table.querySelectorAll('th[data-sort-index] button');

    buttons.forEach(function (button) {
      button.addEventListener('click', function () {
        sortTable(
          table,
          buttons,
          sortState,
          Number(button.closest('th').dataset.sortIndex)
        );
      });
    });
    updateHeaders(buttons, sortState);
  });
}());
