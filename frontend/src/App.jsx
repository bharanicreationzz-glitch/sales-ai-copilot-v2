import { useEffect, useState } from "react";
import "./App.css";
import "./styles/command-center.css";
import RobotMascot from "./components/RobotMascot";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function App() {
  const [leads, setLeads] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [isEditing, setIsEditing] = useState(false);

  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessingCall, setIsProcessingCall] = useState(false);
  const [callStatus, setCallStatus] = useState("");
  const [callHistory, setCallHistory] = useState([]);
  const [salesCoach, setSalesCoach] = useState(null);
  const [isGeneratingCoach, setIsGeneratingCoach] = useState(false);
  const [coachStatus, setCoachStatus] = useState("");

  const emptyForm = {
    customer_name: "",
    phone: "",
    product: "",
    customer_category: "",
    language: "",
    lead_potential: "Warm",
    quantity: "",
    city: "",
    next_follow_up_date: "",
    notes: "",
    ai_summary: "Manual lead entry",
  };

  const [formData, setFormData] = useState(emptyForm);

  const fetchLeads = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/leads/`);

      if (!response.ok) {
        throw new Error("Failed to fetch leads");
      }

      const data = await response.json();
      setLeads(data);
    } catch (error) {
      console.error("Error fetching leads:", error);
    }
  };

  const fetchCallHistory = async (leadId) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/leads/${leadId}/calls`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch call history");
      }

      const data = await response.json();
      setCallHistory(data);
    } catch (error) {
      console.error("Error fetching call history:", error);
      setCallHistory([]);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch(`${API_BASE_URL}/leads/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...formData,
          product: formData.product || null,
          customer_category: formData.customer_category || null,
          language: formData.language || null,
          next_follow_up_date: formData.next_follow_up_date || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();

        console.error("Backend validation error:", errorData);

        alert(
          JSON.stringify(
            errorData.detail || "Failed to create lead",
            null,
            2
          )
        );

        return;
      }

      setShowForm(false);
      setFormData({ ...emptyForm });
      await fetchLeads();
    } catch (error) {
      console.error("Error creating lead:", error);
      alert(`Error creating lead: ${error.message}`);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();

    if (!selectedLead) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/leads/${selectedLead.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...formData,
            product: formData.product || null,
            customer_category: formData.customer_category || null,
            language: formData.language || null,
            next_follow_up_date: formData.next_follow_up_date || null,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || "Failed to update lead"
        );
      }

      const updatedLead = await response.json();

      setSelectedLead(updatedLead);
      setIsEditing(false);

      await fetchLeads();
    } catch (error) {
      console.error("Error updating lead:", error);
      alert(`Error updating lead: ${error.message}`);
    }
  };

  const handleCallProcessing = async () => {
    if (!selectedLead) {
      alert("Please select a lead first");
      return;
    }

    if (!selectedFile) {
      alert("Please select an audio recording first");
      return;
    }

    try {
      setIsProcessingCall(true);

      // STEP 1: Upload the recording.
      setCallStatus("Uploading call recording...");

      const formDataUpload = new FormData();
      formDataUpload.append("file", selectedFile);

      const uploadResponse = await fetch(
        `${API_BASE_URL}/leads/${selectedLead.id}/calls`,
        {
          method: "POST",
          body: formDataUpload,
        }
      );

      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json().catch(() => ({}));
        throw new Error(
          errorData.detail || "Failed to upload recording"
        );
      }

      const uploadData = await uploadResponse.json();
      const callId = uploadData.call_record_id;

      if (!callId) {
        throw new Error("The upload response did not include a call ID");
      }

      await fetchCallHistory(selectedLead.id);

      // STEP 2: Transcribe the recording.
      setCallStatus("Transcribing audio...");

      const transcribeResponse = await fetch(
        `${API_BASE_URL}/leads/calls/${callId}/transcribe`,
        {
          method: "POST",
        }
      );

      if (!transcribeResponse.ok) {
        const errorData = await transcribeResponse.json().catch(() => ({}));
        throw new Error(
          errorData.detail || "Failed to transcribe recording"
        );
      }

      await fetchCallHistory(selectedLead.id);

      // STEP 3: Analyze the conversation.
      setCallStatus("AI is analyzing the sales conversation...");

      const analyzeResponse = await fetch(
        `${API_BASE_URL}/leads/calls/${callId}/analyze`,
        {
          method: "POST",
        }
      );

      if (!analyzeResponse.ok) {
        const errorData = await analyzeResponse.json().catch(() => ({}));
        throw new Error(
          errorData.detail || "Failed to analyze call"
        );
      }

      // STEP 4: Refresh the lead data.
      setCallStatus("Refreshing lead information...");

      const updatedLeadResponse = await fetch(
        `${API_BASE_URL}/leads/${selectedLead.id}`
      );

      if (!updatedLeadResponse.ok) {
        throw new Error("Failed to refresh lead");
      }

      const updatedLead = await updatedLeadResponse.json();

      setSelectedLead(updatedLead);
      await fetchLeads();
      await fetchCallHistory(selectedLead.id);

      setCallStatus(
        "AI analysis complete! Lead updated successfully."
      );

      setSelectedFile(null);
      setSalesCoach(null);
      setCoachStatus("");
    } catch (error) {
      console.error("Error processing call:", error);
      setCallStatus(`Error: ${error.message}`);
    } finally {
      setIsProcessingCall(false);
    }
  };

  const generateSalesCoach = async () => {
    if (!selectedLead) {
      return;
    }

    if (!callHistory.length) {
      alert("There is no call history available for coaching.");
      return;
    }

    try {
      setIsGeneratingCoach(true);
      setCoachStatus(
        "AI is studying the complete customer journey..."
      );
      setSalesCoach(null);

      const response = await fetch(
        `${API_BASE_URL}/leads/${selectedLead.id}/sales-coach`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          errorText || "Failed to generate sales coaching"
        );
      }

      const data = await response.json();

      setSalesCoach(data.sales_coach || null);
      setCoachStatus("Coaching is ready.");
    } catch (error) {
      console.error("Error generating sales coach:", error);
      setCoachStatus(`Coaching error: ${error.message}`);
    } finally {
      setIsGeneratingCoach(false);
    }
  };

  const openEditLead = () => {
    if (!selectedLead) return;

    setFormData({
      customer_name: selectedLead.customer_name || "",
      phone: selectedLead.phone || "",
      product: selectedLead.product || "",
      customer_category: selectedLead.customer_category || "",
      language: selectedLead.language || "",
      lead_potential: selectedLead.lead_potential || "Warm",
      quantity: selectedLead.quantity || "",
      city: selectedLead.city || "",
      next_follow_up_date: selectedLead.next_follow_up_date || "",
      notes: selectedLead.notes || "",
      ai_summary: selectedLead.ai_summary || "",
    });

    setIsEditing(true);
  };

  const closeDetails = () => {
    setSelectedLead(null);
    setIsEditing(false);
    setSelectedFile(null);
    setCallStatus("");
    setCallHistory([]);
    setSalesCoach(null);
    setCoachStatus("");
  };

  const renderLeadFormFields = () => (
    <>
      <div className="form-grid">
        <div className="form-group">
          <label>Customer Name *</label>
          <input
            name="customer_name"
            value={formData.customer_name}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label>Phone *</label>
          <input
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label>Product</label>
          <select
            name="product"
            value={formData.product}
            onChange={handleChange}
          >
            <option value="">Select Product</option>
            <option value="Polyhex">Polyhex</option>
            <option value="Checks Mesh">Checks Mesh</option>
            <option value="Trinity Fence Pole">Trinity Fence Pole</option>
            <option value="Lato Fence">Lato Fence</option>
            <option value="Privezy Wall">Privezy Wall</option>
            <option value="Plant Wire">Plant Wire</option>
          </select>
        </div>

        <div className="form-group">
          <label>Quantity</label>
          <input
            name="quantity"
            value={formData.quantity}
            onChange={handleChange}
            placeholder="Example: 800 feet"
          />
        </div>

        <div className="form-group">
          <label>City</label>
          <input
            name="city"
            value={formData.city}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label>Customer Category</label>
          <select
            name="customer_category"
            value={formData.customer_category}
            onChange={handleChange}
          >
            <option value="">Select</option>
            <option value="B2B">B2B</option>
            <option value="B2C">B2C</option>
            <option value="Dealer">Dealer</option>
          </select>
        </div>

        <div className="form-group">
          <label>Language</label>
          <select
            name="language"
            value={formData.language}
            onChange={handleChange}
          >
            <option value="">Select Language</option>
            <option value="English">English</option>
            <option value="Tamil">Tamil</option>
            <option value="Telugu">Telugu</option>
            <option value="Kannada">Kannada</option>
            <option value="Malayalam">Malayalam</option>
            <option value="Hindi">Hindi</option>
          </select>
        </div>

        <div className="form-group">
          <label>Lead Potential</label>
          <select
            name="lead_potential"
            value={formData.lead_potential}
            onChange={handleChange}
          >
            <option value="Hot">Hot</option>
            <option value="Warm">Warm</option>
            <option value="Cold">Cold</option>
          </select>
        </div>

        <div className="form-group">
          <label>Next Follow-up Date</label>
          <input
            type="date"
            name="next_follow_up_date"
            value={formData.next_follow_up_date}
            onChange={handleChange}
          />
        </div>
      </div>

      <div className="form-group">
        <label>Notes</label>
        <textarea
          name="notes"
          value={formData.notes}
          onChange={handleChange}
          rows="4"
        />
      </div>
    </>
  );

  return (
    <div className="app cc-app">
      <header className="header cc-header">
        <div>
          <h1>Sales AI Copilot</h1>
          <p>AI-powered lead management</p>
        </div>

        <button
          className="add-button"
          onClick={() => {
            setFormData({ ...emptyForm });
            setShowForm(true);
          }}
        >
          + Add Lead
        </button>
      </header>

      <main className="container cc-container">
        <div className="page-title">
          <div>
            <h2>Leads</h2>
            <p>Manage and track your sales opportunities</p>
          </div>
        </div>

        {/* ADD NEW LEAD MODAL */}
        {showForm && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h2>Add New Lead</h2>

                <button
                  type="button"
                  className="close-button"
                  onClick={() => setShowForm(false)}
                >
                  ×
                </button>
              </div>

              <form onSubmit={handleSubmit}>
                {renderLeadFormFields()}

                <div className="form-actions">
                  <button
                    type="button"
                    className="cancel-button"
                    onClick={() => setShowForm(false)}
                  >
                    Cancel
                  </button>

                  <button type="submit" className="save-button">
                    Save Lead
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* LEADS TABLE */}
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Phone</th>
                <th>Product</th>
                <th>City</th>
                <th>Potential</th>
                <th>Next Follow-up</th>
              </tr>
            </thead>

            <tbody>
              {leads.length > 0 ? (
                leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="lead-row"
                    onClick={() => {
                      setSelectedLead(lead);
                      setIsEditing(false);
                      setSelectedFile(null);
                      setCallStatus("");
                      setCallHistory([]);
                      setSalesCoach(null);
                      setCoachStatus("");
                      fetchCallHistory(lead.id);
                    }}
                  >
                    <td>{lead.customer_name}</td>
                    <td>{lead.phone}</td>
                    <td>{lead.product || "-"}</td>
                    <td>{lead.city || "-"}</td>
                    <td>
                      <span
                        className={`badge ${lead.lead_potential?.toLowerCase()}`}
                      >
                        {lead.lead_potential || "NA"}
                      </span>
                    </td>
                    <td>{lead.next_follow_up_date || "-"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="empty">
                    No leads found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* LEAD DETAILS MODAL */}
        {selectedLead && (
          <div className="modal-overlay" onClick={closeDetails}>
            <div
              className="modal details-modal"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-header">
                <div>
                  <h2>{selectedLead.customer_name}</h2>
                  <p className="lead-id">Lead #{selectedLead.id}</p>
                </div>

                <div className="modal-actions">
                  {!isEditing && (
                    <button
                      className="edit-button"
                      onClick={openEditLead}
                    >
                      Edit Lead
                    </button>
                  )}

                  <button
                    className="close-button"
                    onClick={closeDetails}
                  >
                    ×
                  </button>
                </div>
              </div>

              {/* EDIT MODE */}
              {isEditing ? (
                <form onSubmit={handleUpdate}>
                  {renderLeadFormFields()}

                  <div className="form-actions">
                    <button
                      type="button"
                      className="cancel-button"
                      onClick={() => setIsEditing(false)}
                    >
                      Cancel
                    </button>

                    <button type="submit" className="save-button">
                      Update Lead
                    </button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="details-grid">
                    <div className="detail-item">
                      <span>Phone</span>
                      <strong>{selectedLead.phone || "-"}</strong>
                    </div>

                    <div className="detail-item">
                      <span>Product</span>
                      <strong>{selectedLead.product || "-"}</strong>
                    </div>

                    <div className="detail-item">
                      <span>Quantity</span>
                      <strong>{selectedLead.quantity || "-"}</strong>
                    </div>

                    <div className="detail-item">
                      <span>City</span>
                      <strong>{selectedLead.city || "-"}</strong>
                    </div>

                    <div className="detail-item">
                      <span>Customer Category</span>
                      <strong>
                        {selectedLead.customer_category || "-"}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Language</span>
                      <strong>{selectedLead.language || "-"}</strong>
                    </div>

                    <div className="detail-item">
                      <span>Lead Potential</span>
                      <strong>
                        <span
                          className={`badge ${selectedLead.lead_potential?.toLowerCase()}`}
                        >
                          {selectedLead.lead_potential || "NA"}
                        </span>
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Next Follow-up</span>
                      <strong>
                        {selectedLead.next_follow_up_date || "-"}
                      </strong>
                    </div>
                  </div>

                  <div className="detail-section">
                    <span>Notes</span>
                    <p>{selectedLead.notes || "-"}</p>
                  </div>

                  <div className="detail-section">
                    <span>AI Summary</span>
                    <p>{selectedLead.ai_summary || "-"}</p>
                  </div>

                  {/* AI CALL ANALYSIS */}
                  <div className="call-upload-section">
                    <h3>AI Call Analysis</h3>

                    <p className="call-upload-description">
                      Upload multiple sales call recordings for this lead.
                      AI will analyze each conversation and update the CRM.
                    </p>

                    {/* CALL HISTORY */}
                    {callHistory.length > 0 && (
                      <div className="call-history">
                        <div className="call-section-header">
                          <div>
                            <h4>Sales Conversation History</h4>
                            <p className="call-upload-description">
                              Each call is evaluated in the context of the
                              customer's complete journey.
                            </p>
                          </div>
                        </div>

                        <div className="call-history-list">
                          {callHistory.map((call, index) => (
                            <div
                              className="call-history-item"
                              key={call.id}
                            >
                              <div className="call-history-left">
                                <div className="call-icon">☎</div>

                                <div className="call-history-info">
                                  <strong>
                                    Call #{call.call_number || index + 1}
                                  </strong>
                                  <span>{call.status || "Analyzed"}</span>
                                </div>
                              </div>

                              <span className="call-status-badge">
                                {call.has_transcript
                                  ? "Transcribed"
                                  : "Pending"}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI SALES COACH */}
                    <section className="sales-coach-section">
                       <RobotMascot
                         title="Your AI Sales Coach"
                         message="Let's review the customer's buying signals, identify missed opportunities, and plan your next sales move."
                       />

  <div className="sales-coach-box">
                        <div className="sales-coach-header">
                          <div>
                            <div className="coach-title-row">
                              <span className="coach-icon">AI</span>
                              <h3>AI Sales Coach</h3>
                            </div>

                            <p>
                              Blunt, evidence-based coaching from the
                              complete customer journey.
                            </p>
                          </div>

                          <button
                            type="button"
                            className="coach-button"
                            onClick={generateSalesCoach}
                            disabled={
                              isGeneratingCoach ||
                              callHistory.length === 0
                            }
                          >
                            {isGeneratingCoach
                              ? "Analysing..."
                              : salesCoach
                              ? "Refresh Coaching"
                              : "Get Coaching"}
                          </button>
                        </div>

                        {coachStatus && (
                          <div className="coach-status">
                            {coachStatus}
                          </div>
                        )}

                        {!salesCoach &&
                          !isGeneratingCoach &&
                          callHistory.length > 0 && (
                            <div className="coach-empty-state">
                              <strong>
                                Ready for a blunt sales review.
                              </strong>
                              <p>
                                AI will study all {callHistory.length}{" "}
                                recorded calls before judging how close this
                                customer is to buying.
                              </p>
                            </div>
                          )}

                        {salesCoach && (
                          <div className="coach-result">
                            <div className="closing-score-card">
                              <div className="closing-score-label">
                                Overall Sales Closing Score
                              </div>

                              <div className="closing-score-value">
                                {salesCoach.closing_score?.score ?? "--"}
                                <span>/100</span>
                              </div>

                              <div className="closing-score-caption">
                                Based only on verified buying signals in the
                                recorded call history.
                              </div>
                            </div>

                            <div className="coach-block coach-positive-block">
                              <div className="coach-block-title">
                                What you did well?
                              </div>

                              <ul className="coach-list">
                                {(salesCoach.what_you_did_well || []).map(
                                  (item, index) => (
                                    <li key={index}>
                                      <span>{item.point}</span>

                                      {item.evidence_verified &&
                                        item.evidence_quote && (
                                          <small>
                                            Call #{item.call_number}: “
                                            {item.evidence_quote}”
                                          </small>
                                        )}
                                    </li>
                                  )
                                )}
                              </ul>
                            </div>

                            <div className="coach-block coach-gap-block">
                              <div className="coach-block-title">
                                What you didn't do well yet?
                              </div>

                              <ul className="coach-list">
                                {(
                                  salesCoach.what_you_didnt_do_well || []
                                ).map((item, index) => (
                                  <li key={index}>
                                    <span>{item.point}</span>

                                    {item.evidence_verified &&
                                      item.evidence_quote && (
                                        <small>
                                          Call #{item.call_number}: “
                                          {item.evidence_quote}”
                                        </small>
                                      )}
                                  </li>
                                ))}
                              </ul>
                            </div>

                            <div className="coach-block coach-action-block">
                              <div className="coach-block-title">
                                What to do now in subsequent calls?
                              </div>

                              <ul className="coach-list">
                                {(salesCoach.what_to_do_now || []).map(
                                  (item, index) => (
                                    <li key={index}>
                                      <span>{item.point}</span>

                                      {item.evidence_verified &&
                                        item.evidence_quote && (
                                          <small>
                                            Based on Call #{item.call_number}:
                                            “{item.evidence_quote}”
                                          </small>
                                        )}
                                    </li>
                                  )
                                )}
                              </ul>
                            </div>
                          </div>
                        )}
                      </div>
                    </section>

                    {/* UPLOAD CALL RECORDING */}
                    <div className="new-call-upload">
                      <h4>
                        {callHistory.length > 0
                          ? "Upload New Call Recording"
                          : "Upload First Call Recording"}
                      </h4>

                      <input
                        type="file"
                        accept=".mp3,.mpeg,.wav,.m4a,audio/mpeg,audio/wav,audio/mp4"
                        onChange={(e) => {
                          setSelectedFile(e.target.files?.[0] || null);
                          setCallStatus("");
                        }}
                      />

                      {selectedFile && (
                        <p className="selected-file">
                          Selected: {selectedFile.name}
                        </p>
                      )}

                      <button
                        type="button"
                        className="analyze-call-button"
                        onClick={handleCallProcessing}
                        disabled={isProcessingCall}
                      >
                        {isProcessingCall
                          ? "Processing..."
                          : callHistory.length > 0
                          ? "+ Upload & Analyze New Call"
                          : "Analyze Call with AI"}
                      </button>
                    </div>

                    {callStatus && (
                      <p className="call-status">{callStatus}</p>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
