def recalculate_all_audits():
    """
    تمام آڈٹس کے اسکور دوبارہ کیلکولیٹ کریں (اگر ڈیٹا میں مسئلہ ہو)
    """
    from .models import Audit
    audits = Audit.objects.all()

    for audit in audits:
        audit.calculate_totals()

    return f"Recalculated {audits.count()} audits"


def recalculate_section_scores(audit_id):
    """
    مخصوص آڈٹ کے تمام سیکشن اسکور دوبارہ کیلکولیٹ کریں
    """
    from .models import AuditSection, Audit
    try:
        audit = Audit.objects.get(id=audit_id)
        sections = audit.auditsection_set.all()

        for section in sections:
            section.calculate_section_score()

        audit.calculate_totals()
        return f"Recalculated {sections.count()} sections for audit {audit_id}"

    except Audit.DoesNotExist:
        return f"Audit with id {audit_id} does not exist"