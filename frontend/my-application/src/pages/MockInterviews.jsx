
import { useState } from "react";
import { useEffect } from "react";
import api from "../api";

const questionBank = {
  DSA: [
    {
      question: "What is the difference between an array and a linked list?",
      points: [
        "Arrays store elements in contiguous memory.",
        "Linked lists connect nodes using pointers or references.",
        "Arrays support direct indexing; linked lists require traversal.",
      ],
    },
    {
      question: "What is the time complexity of binary search?",
      points: [
        "Time complexity is O(log n).",
        "The search interval is halved in each iteration.",
        "The input must be sorted.",
      ],
    },
    {
      question: "Explain a stack and its common operations.",
      points: [
        "A stack follows Last In, First Out (LIFO).",
        "Push inserts an element.",
        "Pop removes the top element.",
      ],
    },
  ],

  JavaScript: [
    {
      question: "What is the difference between let, const and var?",
      points: [
        "var is function-scoped.",
        "let and const are block-scoped.",
        "const prevents reassignment of the binding.",
      ],
    },
    {
      question: "What is a JavaScript Promise?",
      points: [
        "A Promise represents the eventual result of an asynchronous operation.",
        "Its states include pending, fulfilled and rejected.",
        "Promises can be handled using then, catch and finally.",
      ],
    },
  ],

  HR: [
    {
      question: "Tell me about yourself.",
      points: [
        "Introduce your academic background.",
        "Mention relevant technical skills and projects.",
        "Explain your career goal and interest in the role.",
      ],
    },
    {
      question: "Describe a challenge you faced in a project.",
      points: [
        "Explain the challenge clearly.",
        "Describe your individual contribution.",
        "Share the result and what you learned.",
      ],
    },
  ],
};

export default function MockInterviews() {
  const [category, setCategory] = useState("DSA");
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [completed, setCompleted] = useState(0);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void api.get("/mock-interviews/history").then((items) => { setHistory(items); setCompleted(items.length); }).catch((err) => setError(err.message));
  }, []);

  const questions = questionBank[category];
  const current = questions[index];

  function changeCategory(value) {
    setCategory(value);
    setIndex(0);
    setAnswer("");
    setShowFeedback(false);
  }

  async function submitAnswer() {
    if (!answer.trim()) {
      alert("Please write your answer before submitting.");
      return;
    }

    setError("");
    try {
      const saved = await api.post("/mock-interviews", { category, question: current.question, answer });
      setHistory((prev) => [{ id: saved.id, category, question: current.question, answer, date: new Date().toLocaleDateString() }, ...prev]);
    } catch (err) { setError(err.message); return; }

    setCompleted((prev) => prev + 1);
    setShowFeedback(true);
  }

  function nextQuestion() {
    setIndex((prev) => (prev + 1) % questions.length);
    setAnswer("");
    setShowFeedback(false);
  }

  return (
    <section className="st-page">
      <div className="st-page-header">
        <div>
          <h1>🎯 Mock Interviews</h1>
          <p>Practice interview questions and improve your answers.</p>
        </div>
      </div>
      {error && <p role="alert">{error}</p>}

      <div className="st-stats-grid">
        <div className="st-card">
          <span>Answers Submitted</span>
          <h2>{completed}</h2>
        </div>

        <div className="st-card">
          <span>Practice Categories</span>
          <h2>{Object.keys(questionBank).length}</h2>
        </div>

        <div className="st-card">
          <span>Saved Attempts</span>
          <h2>{history.length}</h2>
        </div>
      </div>

      <div className="st-card st-interview-card">
        <label htmlFor="interview-category">Choose interview category</label>

        <select
          id="interview-category"
          value={category}
          onChange={(e) => changeCategory(e.target.value)}
        >
          {Object.keys(questionBank).map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>

        <div className="st-question-count">
          Question {index + 1} of {questions.length}
        </div>

        <h2>{current.question}</h2>

        <textarea
          rows="7"
          placeholder="Write your answer here..."
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          disabled={showFeedback}
        />

        {!showFeedback ? (
          <button className="st-primary-btn" onClick={submitAnswer}>
            Submit Answer
          </button>
        ) : (
          <div className="st-feedback">
            <h3>📝 Answer Review Checklist</h3>
            <p>
              Compare your answer with the key concepts below. This is a
              self-review checklist, not an automated AI evaluation.
            </p>

            <ul>
              {current.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>

            <button className="st-primary-btn" onClick={nextQuestion}>
              Next Question →
            </button>
          </div>
        )}
      </div>

      {history.length > 0 && (
        <div className="st-card st-history">
          <h3>Recent Practice Attempts</h3>

          {history.slice(0, 5).map((item, i) => (
            <div className="st-history-item" key={`${item.date}-${i}`}>
              <strong>{item.category}</strong>
              <p>{item.question}</p>
              <span className="st-muted">{item.date}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

