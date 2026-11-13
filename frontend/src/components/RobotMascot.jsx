import React from "react";

export default function RobotMascot({
  title = "Your AI Sales Coach",
  message = "I'm ready to help you with your next sales conversation.",
  compact = false,
}) {
  return (
    <section
      className={`robot-assistant ${compact ? "robot-assistant--compact" : ""}`}
      aria-label="AI Sales Coach assistant"
    >
      <div className="robot-scene" aria-hidden="true">
        <div className="robot-glow" />

        <div className="robot">
          <div className="robot-antenna">
            <span />
          </div>

          <div className="robot-head">
            <div className="robot-ear robot-ear--left" />
            <div className="robot-ear robot-ear--right" />

            <div className="robot-face">
              <span className="robot-eye" />
              <span className="robot-eye" />
              <span className="robot-smile" />
            </div>
          </div>

          <div className="robot-neck" />

          <div className="robot-body">
            <span className="robot-core">
              <span />
            </span>
          </div>

          <div className="robot-arm robot-arm--left" />
          <div className="robot-arm robot-arm--right" />
        </div>

        <div className="robot-platform" />
      </div>

      <div className="robot-assistant__content">
        <span className="robot-eyebrow">
          <span className="robot-status-dot" />
          AI ASSISTANT
        </span>

        <h3>{title}</h3>
        <p>{message}</p>
      </div>
    </section>
  );
}