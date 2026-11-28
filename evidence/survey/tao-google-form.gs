/**
 * Tạo Google Form "Phiếu tìm hiểu: học với video pre-class" — cùng nội dung với
 * evidence/interviews/phieu-hoc-vien-tu-dien.docx.
 *
 * Cách dùng (1–2 phút):
 *   1. Mở https://script.google.com → New project → xoá code mẫu → dán toàn bộ file này.
 *   2. Chọn hàm taoForm ở thanh trên → Run → cho phép quyền (Google Forms, Google Sheets).
 *   3. Xem View → Logs (hoặc Execution log): có link điền (gửi học viên) và link sửa (giữ cho nhóm).
 *
 * Form KHÔNG thu email, không bắt đăng nhập, không hỏi tên / SĐT / mã học viên.
 * Câu trả lời đổ về một Google Sheet mới (link cũng in ở Logs) để nhóm đếm.
 */
function taoForm() {
  const form = FormApp.create('Phiếu tìm hiểu: học với video pre-class');
  form.setDescription(
    'Nhóm Aurora (AI20K L3B) đang tìm hiểu các bạn làm gì khi gặp chỗ chưa hiểu lúc xem video pre-class. ' +
    'Phiếu không giới thiệu sản phẩm nào và không có câu trả lời đúng hay sai. Khoảng 10 phút.\n\n' +
    '• Hãy trả lời theo lần thật sự đã xảy ra gần nhất, không phải theo thói quen chung. Không nhớ thì ghi "không nhớ".\n' +
    '• Không ghi tên, số điện thoại, email hay mã học viên ở bất kỳ đâu trong phiếu.\n' +
    '• Câu trả lời chỉ dùng tổng hợp ẩn danh cho bài nộp hackathon của nhóm.');
  form.setCollectEmail(false);
  try { form.setRequireLogin(false); } catch (e) { /* chỉ có ở tài khoản Workspace */ }
  form.setAllowResponseEdits(false);
  form.setProgressBar(true);
  form.setConfirmationMessage('Cảm ơn bạn! Câu trả lời đã được ghi lại (không kèm thông tin cá nhân).');

  form.addCheckboxItem()
    .setTitle('Đồng ý')
    .setChoiceValues(['Mình đồng ý cho nhóm dùng câu trả lời (đã bỏ thông tin cá nhân) trong bài hackathon.'])
    .setRequired(true);

  // ---------- A ----------
  form.addPageBreakItem().setTitle('A. Về bạn');
  form.addMultipleChoiceItem()
    .setTitle('A1. Bạn là:')
    .setChoiceValues(['Học viên L3B đang đi làm', 'Học viên L3B là sinh viên', 'Học viên L3A'])
    .showOtherOption(true)
    .setRequired(true);
  form.addTextItem()
    .setTitle('A2. Trong 1 tháng qua, bạn xem khoảng bao nhiêu video pre-class?')
    .setHelpText('Ghi một con số, hoặc "không nhớ".');

  // ---------- B ----------
  form.addPageBreakItem().setTitle('B. Lần gần nhất bạn gặp chỗ chưa hiểu khi xem video');
  form.addParagraphTextItem()
    .setTitle('B1. Lần gần nhất là khi nào? Video / bài nào, đoạn đó nói về gì?')
    .setHelpText('Ví dụ cách ghi: "tối thứ Năm, video Day08, đoạn nói về …"')
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle('B2. Lúc đó bạn đã làm gì? Kể lại theo thứ tự.')
    .setRequired(true);
  form.addCheckboxItem()
    .setTitle('B2 (thêm). Nếu tiện, đánh dấu những việc bạn đã làm lần đó:')
    .setChoiceValues(['Hỏi trợ giảng AI dưới video', 'Tua lại video', 'Hỏi bạn / nhóm',
                      'Tìm Google / ChatGPT', 'Hỏi TA / giảng viên', 'Bỏ qua, học tiếp'])
    .showOtherOption(true);
  form.addCheckboxItem()
    .setTitle('B3. Nếu lần đó bạn có hỏi trợ giảng AI: đọc câu trả lời xong, bạn làm gì tiếp?')
    .setChoiceValues(['Dùng luôn câu trả lời', 'Tua lại video để đối chiếu', 'Hỏi tiếp trợ giảng',
                      'Tìm nguồn khác', 'Lần đó không hỏi trợ giảng']);
  form.addParagraphTextItem()
    .setTitle('B3 (tiếp). Vì sao bạn làm vậy?');
  form.addParagraphTextItem()
    .setTitle('B4. Bạn có kiểm câu trả lời đó có đúng với bài giảng không? Nếu có, kiểm bằng cách nào?');
  form.addTextItem()
    .setTitle('B5. Từ lúc gặp chỗ chưa hiểu đến lúc xong (hiểu ra hoặc bỏ qua) mất khoảng bao nhiêu phút?')
    .setHelpText('Ghi số phút, hoặc "không nhớ".');

  // ---------- C ----------
  form.addPageBreakItem().setTitle('C. Trong 1 tháng qua');
  form.addTextItem()
    .setTitle('C1. Chuyện gặp chỗ chưa hiểu khi xem video như vậy xảy ra khoảng mấy lần?')
    .setHelpText('Ghi số lần, hoặc "không nhớ".');
  form.addMultipleChoiceItem()
    .setTitle('C2. Có lần nào bạn tin một câu trả lời (của trợ giảng AI hay nguồn khác) rồi sau đó thấy nó sai hoặc không khớp với bài không?')
    .setChoiceValues(['Có', 'Không', 'Không nhớ']);
  form.addParagraphTextItem()
    .setTitle('C2 (tiếp). Nếu có: kể lại lần đó, và chuyện gì xảy ra sau.')
    .setHelpText('Ví dụ: làm sai lab, mất thời gian hỏi lại…');
  form.addParagraphTextItem()
    .setTitle('C3. Điều gì khó chịu nhất ở cách bạn đang làm khi gặp chỗ chưa hiểu? Vì sao bạn vẫn dùng cách đó?');

  // ---------- D ----------
  form.addPageBreakItem().setTitle('D. Tuỳ chọn');
  form.addMultipleChoiceItem()
    .setTitle('D1. Bạn có sẵn lòng dùng thử một bản demo khoảng 10 phút không?')
    .setHelpText('Nếu có, báo trực tiếp với bạn gửi phiếu. Đừng ghi cách liên lạc vào phiếu.')
    .setChoiceValues(['Có', 'Không']);

  // Câu trả lời → Google Sheet mới để nhóm đếm
  const ss = SpreadsheetApp.create('Phiếu tìm hiểu pre-class — câu trả lời');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  Logger.log('Link gửi học viên điền: ' + form.getPublishedUrl());
  Logger.log('Link sửa form (chỉ nhóm): ' + form.getEditUrl());
  Logger.log('Sheet câu trả lời: ' + ss.getUrl());
}
