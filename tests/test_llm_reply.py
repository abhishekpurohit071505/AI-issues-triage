from unittest.mock import Mock, patch
import sys
import types
from llm_reply import generate_reply, validate_reply, llm_enabled

TICKET = {"id": "TKT-003", "text": "I can see another company's invoices and customer names."}
ANALYSIS = {"category": "Security", "priority": "P1", "team": "Security Incident Response"}
FALLBACK = "Hello, thank you for reporting this potential exposure. Reference: TKT-003. FlowDesk Support"


def test_no_key_uses_fallback():
    with patch("llm_reply.get_setting", side_effect=lambda n, default="": {"USE_LLM": "1", "OPENAI_API_KEY": ""}.get(n, default)):
        out=generate_reply(TICKET, ANALYSIS, FALLBACK)
        assert out.reply == FALLBACK
        assert "template" in out.source.lower()


def test_unsafe_facts_rejected():
    msg="Hello, we have issued a refund. We are reviewing your request. Reference: TKT-003. FlowDesk Support"
    assert validate_reply(msg,"TKT-003") is not None
    msg="Hello, the issue is resolved and your account is now secure. Reference: TKT-003. FlowDesk Support"
    assert validate_reply(msg,"TKT-003") is not None


def test_reference_required():
    assert validate_reply("Thank you for your report. The security team should review this and we will follow up by secure means.", "TKT-003")


def test_llm_sensitive_incident_can_draft_but_only_for_review():
    safe="Hello, thank you for reporting this concern. We understand the potential impact. This requires urgent security review. Please do not share other customers' information here. Reference: TKT-003. FlowDesk Support"
    response=Mock()
    response.choices=[Mock(message=Mock(content='{"proposed_reply": '+__import__('json').dumps(safe)+'}'))]
    fake_client=Mock()
    fake_client.chat.completions.create.return_value=response
    with patch("llm_reply.llm_enabled", return_value=True), patch("llm_reply.get_setting", side_effect=lambda n,default="": {"OPENAI_API_KEY":"fake-key","OPENAI_MODEL":"test-model"}.get(n,default)):
        with patch.dict(sys.modules, {"openai": types.SimpleNamespace(OpenAI=lambda **kw: fake_client)}):
            out=generate_reply(TICKET,ANALYSIS,FALLBACK,"Empathetic")
    assert out.reply == safe
    assert "OpenAI" in out.source
    assert fake_client.chat.completions.create.call_count == 1
