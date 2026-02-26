const {
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Box,
  Stack,
  Chip,
  Paper,
  Button,
  Divider,
  List,
  ListItemButton,
  ListItemText,
  TextField,
  Drawer,
  Snackbar,
  Alert
} = MaterialUI;

const useMediaQuery = MaterialUI.useMediaQuery;
const { useEffect, useMemo, useRef, useState } = React;

marked.setOptions({ breaks: true, gfm: true });

const STARTER_PROMPTS = [
  "How is our pipeline trending this quarter?",
  "Which sector has the highest total deal value?",
  "Show all in-progress work orders and blockers.",
  "Compare expected pipeline value against billed amount.",
  "Which deal owners have the most open opportunities?",
  "Give me a Powerline sector health snapshot."
];

const BOARDS = [
  { name: "Deals Pipeline", meta: "346 records available" },
  { name: "Work Orders Tracker", meta: "177 records available" }
];

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#0e7490" },
    secondary: { main: "#ea580c" },
    background: {
      default: "transparent",
      paper: "rgba(255, 255, 255, 0.9)"
    },
    text: {
      primary: "#0f172a",
      secondary: "#475569"
    }
  },
  shape: {
    borderRadius: 16
  },
  typography: {
    fontFamily: "Sora, system-ui, sans-serif",
    h6: { fontWeight: 700, letterSpacing: "-0.02em" },
    body2: { lineHeight: 1.6 }
  }
});

function safeMarkdown(markdownText) {
  const html = marked.parse(markdownText || "");
  return window.DOMPurify ? DOMPurify.sanitize(html) : html;
}

function traceFriendlyName(name) {
  const map = {
    query_deals_board: "Deals Pipeline",
    query_work_orders_board: "Work Orders",
    cross_board_analysis: "Cross-board analysis"
  };
  return map[name] || name || "Unknown tool";
}

function statusColor(runState) {
  if (runState === "Thinking") return "warning";
  if (runState === "Streaming") return "secondary";
  if (runState === "Error") return "error";
  return "success";
}

function createId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function SidePanel({ onPromptSelect, onClearConversation, asDrawer = false }) {
  return (
    <Paper className={asDrawer ? "panel-surface drawer-surface" : "panel-surface"} elevation={0}>
      <Stack spacing={2.25} sx={{ height: "100%" }}>
        <Box>
          <Typography variant="overline" className="panel-overline">Connected Boards</Typography>
          <Stack spacing={1} sx={{ mt: 1 }}>
            {BOARDS.map((board) => (
              <Paper key={board.name} className="board-card" elevation={0}>
                <Box>
                  <Typography fontWeight={700} fontSize={14}>{board.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{board.meta}</Typography>
                </Box>
                <Chip size="small" label="LIVE" color="success" variant="outlined" />
              </Paper>
            ))}
          </Stack>
        </Box>

        <Box className="grow">
          <Typography variant="overline" className="panel-overline">Starter Prompts</Typography>
          <List dense className="prompt-list">
            {STARTER_PROMPTS.map((prompt) => (
              <ListItemButton
                key={prompt}
                className="prompt-item"
                onClick={() => onPromptSelect(prompt)}
              >
                <ListItemText primary={prompt} />
              </ListItemButton>
            ))}
          </List>
        </Box>

        <Button variant="outlined" fullWidth onClick={onClearConversation}>New conversation</Button>
      </Stack>
    </Paper>
  );
}

function TracePanel({ traces, onClearTrace, asDrawer = false }) {
  return (
    <Paper className={asDrawer ? "panel-surface drawer-surface" : "panel-surface"} elevation={0}>
      <Stack spacing={1.5} sx={{ height: "100%" }}>
        <Box className="trace-head">
          <Typography variant="h6" fontSize={17}>Agent Trace</Typography>
          <Chip
            size="small"
            label={String(traces.length)}
            color={traces.length ? "primary" : "default"}
            variant={traces.length ? "filled" : "outlined"}
          />
          <Button size="small" onClick={onClearTrace}>Clear</Button>
        </Box>

        <Divider />

        <Box className="trace-scroll">
          {traces.length === 0 && (
            <Paper className="trace-empty" elevation={0}>
              <Typography fontWeight={700}>No events yet</Typography>
              <Typography variant="body2" color="text.secondary">
                Tool calls and data fetch results will appear here in real time.
              </Typography>
            </Paper>
          )}

          <Stack spacing={1.2}>
            {traces.map((trace) => {
              const resolvedCall = trace.type === "tool_call" && trace.resolved;
              const cardKind = trace.type === "error" ? "error" : resolvedCall || trace.type === "tool_result" ? "result" : "call";

              return (
                <Paper key={trace.id} className={`trace-card ${cardKind}`} elevation={0}>
                  <Box className="trace-top-row">
                    <Typography fontWeight={700} fontSize={13}>
                      {traceFriendlyName(trace.name)}
                    </Typography>
                    <Chip
                      size="small"
                      className="trace-chip"
                      label={cardKind === "error" ? "ERROR" : cardKind === "call" ? "CALL" : "RESULT"}
                      color={cardKind === "error" ? "error" : cardKind === "call" ? "warning" : "success"}
                      variant="outlined"
                    />
                  </Box>

                  {cardKind === "call" && (
                    <Typography variant="body2" color="text.secondary">
                      Starting API read...
                    </Typography>
                  )}

                  {cardKind === "result" && (
                    <Typography variant="body2" color="text.secondary">
                      <strong>{trace.item_count || 0}</strong> records returned.
                    </Typography>
                  )}

                  {cardKind === "error" && (
                    <Typography variant="body2" color="text.secondary">
                      {trace.message || "Unknown error"}
                    </Typography>
                  )}
                </Paper>
              );
            })}
          </Stack>
        </Box>
      </Stack>
    </Paper>
  );
}

function App() {
  const [history, setHistory] = useState([]);
  const [messages, setMessages] = useState([]);
  const [traces, setTraces] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [runState, setRunState] = useState("Idle");
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [toast, setToast] = useState({ open: false, message: "", severity: "success" });

  const inputRef = useRef(null);
  const streamRef = useRef(null);

  const isCompact = useMediaQuery(theme.breakpoints.down("lg"));

  const welcomeVisible = messages.length === 0;
  const statusChipColor = useMemo(() => statusColor(runState), [runState]);

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [messages, traces, streaming]);

  useEffect(() => {
    const handleShortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (inputRef.current) inputRef.current.focus();
      }

      if (event.key === "Escape") {
        setLeftOpen(false);
        setRightOpen(false);
      }
    };

    document.addEventListener("keydown", handleShortcut);
    return () => document.removeEventListener("keydown", handleShortcut);
  }, []);

  const showToast = (message, severity = "success") => {
    setToast({ open: true, message, severity });
  };

  const clearTrace = () => setTraces([]);

  const clearConversation = () => {
    setHistory([]);
    setMessages([]);
    setTraces([]);
    setInput("");
    setRunState("Idle");
    setStreaming(false);
    showToast("Conversation cleared");
  };

  const addTraceCall = (event) => {
    setTraces((prev) => [
      ...prev,
      {
        id: createId(),
        type: "tool_call",
        name: event.name || "unknown_tool",
        args: event.args || {},
        resolved: false
      }
    ]);
  };

  const addTraceResult = (event) => {
    setTraces((prev) => {
      const next = [...prev];
      const index = [...next]
        .reverse()
        .findIndex((item) => item.type === "tool_call" && !item.resolved && item.name === event.name);

      if (index !== -1) {
        const targetIndex = next.length - 1 - index;
        next[targetIndex] = {
          ...next[targetIndex],
          resolved: true,
          item_count: event.item_count || 0
        };
        return next;
      }

      next.push({
        id: createId(),
        type: "tool_result",
        name: event.name || "unknown_tool",
        item_count: event.item_count || 0
      });
      return next;
    });
  };

  const addTraceError = (event) => {
    setTraces((prev) => [
      ...prev,
      {
        id: createId(),
        type: "error",
        name: "Runtime error",
        message: event.message || "Unknown error"
      }
    ]);
  };

  const pushUserMessage = (text) => {
    setMessages((prev) => [
      ...prev,
      { id: createId(), role: "user", content: text, timestamp: new Date() }
    ]);
  };

  const pushAssistantMessage = (text) => {
    setMessages((prev) => [
      ...prev,
      { id: createId(), role: "assistant", content: text, timestamp: new Date() }
    ]);
  };

  const handlePromptSelect = (prompt) => {
    setInput(prompt);
    void sendMessage(prompt);
  };

  const sendMessage = async (override) => {
    const text = (override ?? input).trim();
    if (!text || streaming) return;

    setStreaming(true);
    setRunState("Thinking");
    setInput("");
    setTraces([]);
    pushUserMessage(text);

    if (isCompact) {
      setLeftOpen(false);
      setRightOpen(false);
    }

    let assistantReply = "";
    let hadError = false;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response stream from server");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;

          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event;
          try {
            event = JSON.parse(raw);
          } catch {
            continue;
          }

          if (event.type === "tool_call") {
            addTraceCall(event);
            setRunState("Thinking");
            continue;
          }

          if (event.type === "tool_result") {
            addTraceResult(event);
            setRunState("Thinking");
            continue;
          }

          if (event.type === "message") {
            assistantReply = event.content || "";
            pushAssistantMessage(assistantReply);
            setRunState("Streaming");
            continue;
          }

          if (event.type === "error") {
            hadError = true;
            addTraceError(event);
            pushAssistantMessage(`**Error:** ${event.message || "Unknown error"}`);
            setRunState("Error");
            continue;
          }

          if (event.type === "done") {
            if (!hadError) setRunState("Idle");
          }
        }
      }
    } catch (error) {
      hadError = true;
      addTraceError({ message: error.message });
      pushAssistantMessage(`**Connection error:** ${error.message}`);
      setRunState("Error");
    }

    if (assistantReply) {
      setHistory((prev) => {
        const next = [
          ...prev,
          { role: "user", content: text },
          { role: "assistant", content: assistantReply }
        ];
        return next.slice(-20);
      });
    }

    if (!hadError) setRunState("Idle");

    setStreaming(false);
    if (inputRef.current) inputRef.current.focus();
  };

  const handleInputKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

      <AppBar position="sticky" elevation={0} className="topbar">
        <Toolbar className="topbar-inner">
          <Box>
            <Typography variant="h6">Skylark BI Agent</Typography>
            <Typography variant="body2" color="text.secondary">React UI with live SSE trace</Typography>
          </Box>

          <Stack direction="row" spacing={1} alignItems="center">
            <Chip label={runState} color={statusChipColor} variant="filled" />
            {isCompact && (
              <>
                <Button size="small" variant="outlined" onClick={() => setLeftOpen(true)}>Prompts</Button>
                <Button size="small" variant="outlined" onClick={() => setRightOpen(true)}>Trace</Button>
              </>
            )}
          </Stack>
        </Toolbar>
      </AppBar>

      <Box className="app-shell">
        {!isCompact && (
          <SidePanel
            onPromptSelect={handlePromptSelect}
            onClearConversation={clearConversation}
          />
        )}

        <Paper className="chat-surface" elevation={0}>
          <Box className="message-stream" ref={streamRef}>
            {welcomeVisible && (
              <Paper className="welcome-card" elevation={0}>
                <Typography className="welcome-kicker">Live business intelligence</Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, mt: 1.2 }}>
                  Ask founder-level questions and inspect each tool call in real time.
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                  The assistant reads Monday boards live, reasons over deals and work orders,
                  and streams both answer and trace.
                </Typography>
              </Paper>
            )}

            <Stack spacing={1.4}>
              {messages.map((message) => {
                const isUser = message.role === "user";
                const timeText = message.timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit"
                });

                return (
                  <Paper
                    key={message.id}
                    className={`message-card ${isUser ? "user" : "assistant"}`}
                    elevation={0}
                  >
                    <Box className="message-meta">
                      <Typography fontWeight={700} fontSize={13}>{isUser ? "You" : "Skylark AI"}</Typography>
                      <Typography variant="caption" color="text.secondary">{timeText}</Typography>
                    </Box>

                    {isUser ? (
                      <Typography variant="body2">{message.content}</Typography>
                    ) : (
                      <div
                        className="message-markdown"
                        dangerouslySetInnerHTML={{ __html: safeMarkdown(message.content) }}
                      />
                    )}

                    {!isUser && (
                      <Box className="message-actions">
                        <Button
                          size="small"
                          onClick={async () => {
                            try {
                              await navigator.clipboard.writeText(message.content);
                              showToast("Response copied");
                            } catch {
                              showToast("Unable to copy response", "error");
                            }
                          }}
                        >
                          Copy
                        </Button>
                      </Box>
                    )}
                  </Paper>
                );
              })}

              {streaming && (
                <Paper className="message-card assistant typing-card" elevation={0}>
                  <Box className="message-meta">
                    <Typography fontWeight={700} fontSize={13}>Skylark AI</Typography>
                    <Typography variant="caption" color="text.secondary">Thinking...</Typography>
                  </Box>
                  <Box className="typing-dots">
                    <span></span><span></span><span></span>
                  </Box>
                </Paper>
              )}
            </Stack>
          </Box>

          <Divider />

          <Box className="composer">
            <TextField
              fullWidth
              multiline
              minRows={1}
              maxRows={6}
              inputRef={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="Ask about pipeline, sector performance, billing, or operations..."
            />

            <Stack direction="row" spacing={1} justifyContent="space-between" sx={{ mt: 1.25 }}>
              <Button variant="text" onClick={() => setLeftOpen(true)}>Browse prompts</Button>
              <Button variant="contained" onClick={() => void sendMessage()} disabled={streaming || !input.trim()}>
                Send
              </Button>
            </Stack>

            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              Enter to send. Shift+Enter for newline. Ctrl/Cmd+K to focus input.
            </Typography>
          </Box>
        </Paper>

        {!isCompact && <TracePanel traces={traces} onClearTrace={clearTrace} />}
      </Box>

      <Drawer anchor="left" open={leftOpen} onClose={() => setLeftOpen(false)}>
        <Box sx={{ width: 330, height: "100%", p: 1.5 }}>
          <SidePanel
            asDrawer
            onPromptSelect={(prompt) => {
              handlePromptSelect(prompt);
              setLeftOpen(false);
            }}
            onClearConversation={() => {
              clearConversation();
              setLeftOpen(false);
            }}
          />
        </Box>
      </Drawer>

      <Drawer anchor="right" open={rightOpen} onClose={() => setRightOpen(false)}>
        <Box sx={{ width: 340, height: "100%", p: 1.5 }}>
          <TracePanel asDrawer traces={traces} onClearTrace={clearTrace} />
        </Box>
      </Drawer>

      <Snackbar
        open={toast.open}
        autoHideDuration={1800}
        onClose={() => setToast((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity={toast.severity} variant="filled" sx={{ width: "100%" }}>
          {toast.message}
        </Alert>
      </Snackbar>
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
