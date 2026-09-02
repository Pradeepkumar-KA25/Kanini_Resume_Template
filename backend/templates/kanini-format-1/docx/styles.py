from docx.shared import Cm, Pt


def apply_format1_page_setup(section) -> None:
    section.page_width = Cm(21.59)
    section.page_height = Cm(27.94)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def set_times(run, bold: bool = False) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = bold