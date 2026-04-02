"""Tests for the Verdict tracer."""

from verdict.core.tracer import Tracer, Trace


class TestTrace:
    def test_create_trace(self):
        t = Trace(name="test", agent_name="test-agent")
        assert t.name == "test"
        assert t.agent_name == "test-agent"
        assert len(t.actions) == 0

    def test_record_tool_call(self):
        t = Trace(name="test")
        action_id = t.record_tool_call("bash", {"command": "ls"})
        assert len(t.actions) == 1
        assert t.actions[0].tool_call is not None
        assert t.actions[0].tool_call.name == "bash"
        assert action_id == t.last_action_id

    def test_record_tool_result(self):
        t = Trace(name="test")
        call_id = t.record_tool_call("bash", {"command": "ls"})
        # Get the tool_call id from the action
        tc_id = t.actions[0].tool_call.id
        result_id = t.record_tool_result(tc_id, output="file.txt")
        assert len(t.actions) == 2
        assert t.actions[1].tool_result is not None
        assert t.actions[1].tool_result.output == "file.txt"

    def test_record_shell_exec(self):
        t = Trace(name="test")
        t.record_shell_exec("npm build", output="ok", exit_code=0)
        assert len(t.actions) == 1
        assert t.actions[0].metadata["exit_code"] == 0

    def test_record_file_write(self):
        t = Trace(name="test")
        t.record_file_write("/tmp/test.txt", content="hello")
        assert len(t.actions) == 1
        assert t.actions[0].content == "/tmp/test.txt"

    def test_record_http_request(self):
        t = Trace(name="test")
        t.record_http_request("GET", "https://example.com", status_code=200)
        assert len(t.actions) == 1
        assert t.actions[0].metadata["status_code"] == 200

    def test_spans(self):
        t = Trace(name="test")
        with t.span("build") as s:
            t.record_shell_exec("npm build", output="ok", exit_code=0)
            assert len(s.actions) == 1
        assert len(t.spans) == 1
        assert t.spans[0].name == "build"

    def test_finalize(self):
        t = Trace(name="test")
        assert t.ended_at is None
        t.finalize()
        assert t.ended_at is not None

    def test_to_dict(self):
        t = Trace(name="test", agent_name="agent")
        t.record_tool_call("bash", {"command": "ls"})
        d = t.to_dict()
        assert d["name"] == "test"
        assert d["agent_name"] == "agent"
        assert d["action_count"] == 1


class TestTracer:
    def test_trace_context_manager(self):
        tracer = Tracer(agent_name="test")
        with tracer.trace("task") as t:
            t.record_tool_call("bash", {"command": "ls"})
        assert len(tracer.traces) == 1
        assert tracer.traces[0].ended_at is not None

    def test_multiple_traces(self):
        tracer = Tracer(agent_name="test")
        with tracer.trace("task1") as t1:
            t1.record_tool_call("bash", {"command": "ls"})
        with tracer.trace("task2") as t2:
            t2.record_tool_call("read", {"path": "file.txt"})
        assert len(tracer.traces) == 2

    def test_get_trace(self):
        tracer = Tracer(agent_name="test")
        with tracer.trace("task") as t:
            pass
        found = tracer.get_trace(t.id)
        assert found is not None
        assert found.id == t.id

    def test_get_trace_not_found(self):
        tracer = Tracer(agent_name="test")
        assert tracer.get_trace("nonexistent") is None
