// ===== Web UI 用 GAS コマンド =====
// シート.gs に追加してください
// 既存の addSchedule(), addReminder() はそのまま残してください

/**
 * Web UI から練習予定を追加する
 * POST {"cmd": "addPractice", "options": {date, place, startTime, endTime, memo}}
 */
function addPractice(options) {
  options = options || {};
  var date = new Date(options.date);
  var title = "練習";
  var description = convertToQueryString({
    place: options.place || "",
    memo: options.memo || "",
    start: options.date + " " + options.startTime + ":00",
    end: options.date + " " + options.endTime + ":00"
  });
  var event = CalendarApp.getDefaultCalendar().createAllDayEvent(title, date, {description: description});
  event.removeAllReminders();
  return ContentService.createTextOutput("success");
}

/**
 * Web UI からリマインダーを追加する
 * POST {"cmd": "addReminder", "options": {deadline, role, person, task, memo, remindDate}}
 */
function addReminder(options) {
  options = options || {};
  var deadline = new Date(options.deadline);
  var title = "リマインダー";
  var description = convertToQueryString({
    job: options.role || "",
    person: options.person || "",
    task: options.task || "",
    memo: options.memo || "",
    remindDate: options.remindDate || "7,3,1",
    finish: "false"
  });
  var event = CalendarApp.getDefaultCalendar().createAllDayEvent(title, deadline, {description: description});
  event.removeAllReminders();
  return ContentService.createTextOutput("success");
}
