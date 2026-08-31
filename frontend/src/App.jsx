import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [leads, setLeads] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [isEditing, setIsEditing] = useState(false);

  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessingCall, setIsProcessingCall] = useState(false);
  const [callStatus, setCallStatus] = useState("");

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

  const fetchLeads = () => {
    fetch("http://127.0.0.1:8000/leads/")
      .then((response) => response.json())
      .then((data) => setLeads(data))
      .catch((error) =>
        console.error("Error fetching leads:", error)
      );
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData({
      ...formData,
      [name]: value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/leads/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...formData,
            product: formData.product || null,
            customer_category:
              formData.customer_category || null,
            language: formData.language || null,
            next_follow_up_date:
              formData.next_follow_up_date || null,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        console.log(
          "Backend validation error:",
          errorData
        );

        alert(
          JSON.stringify(
            errorData.detail,
            null,
            2
          )
        );

        throw new Error("Failed to create lead");
      }

      setShowForm(false);
      setFormData(emptyForm);

      fetchLeads();

    } catch (error) {
      console.error(error);
      alert("Error creating lead");
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/leads/${selectedLead.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...formData,
            product: formData.product || null,
            customer_category:
              formData.customer_category || null,
            language: formData.language || null,
            next_follow_up_date:
              formData.next_follow_up_date || null,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to update lead");
      }

      const updatedLead = await response.json();

      setSelectedLead(updatedLead);
      setIsEditing(false);

      fetchLeads();

    } catch (error) {
      console.error(error);
      alert("Error updating lead");
    }
  };

  const handleCallProcessing = async () => {
    if (!selectedFile) {
      alert("Please select an audio recording first");
      return;
    }

    try {
      setIsProcessingCall(true);

      // STEP 1 — Upload recording
      setCallStatus("Uploading call recording...");

      const formDataUpload = new FormData();

      formDataUpload.append(
        "file",
        selectedFile
      );

      const uploadResponse = await fetch(
        `http://127.0.0.1:8000/leads/${selectedLead.id}/calls`,
        {
          method: "POST",
          body: formDataUpload,
        }
      );

      if (!uploadResponse.ok) {
        throw new Error("Failed to upload recording");
      }

      const uploadData = await uploadResponse.json();

      const callId = uploadData.call_record_id;


      // STEP 2 — Transcribe recording
      setCallStatus("Transcribing audio with Whisper...");

      const transcribeResponse = await fetch(
        `http://127.0.0.1:8000/leads/calls/${callId}/transcribe`,
        {
          method: "POST",
        }
      );

      if (!transcribeResponse.ok) {
        throw new Error("Failed to transcribe recording");
      }


      // STEP 3 — Analyze with AI
      setCallStatus(
        "AI is analyzing the sales conversation..."
      );

      const analyzeResponse = await fetch(
        `http://127.0.0.1:8000/leads/calls/${callId}/analyze`,
        {
          method: "POST",
        }
      );

      if (!analyzeResponse.ok) {
        throw new Error("Failed to analyze call");
      }


      // STEP 4 — Refresh lead data
      const updatedLeadResponse = await fetch(
        `http://127.0.0.1:8000/leads/${selectedLead.id}`
      );

      const updatedLead =
        await updatedLeadResponse.json();

      setSelectedLead(updatedLead);

      fetchLeads();

      setCallStatus(
        "AI analysis complete! Lead updated successfully."
      );

      setSelectedFile(null);

    } catch (error) {
      console.error(error);

      setCallStatus(
        `Error: ${error.message}`
      );

    } finally {
      setIsProcessingCall(false);
    }
  };

  const openEditLead = () => {
    setFormData({
      customer_name:
        selectedLead.customer_name || "",
      phone:
        selectedLead.phone || "",
      product:
        selectedLead.product || "",
      customer_category:
        selectedLead.customer_category || "",
      language:
        selectedLead.language || "",
      lead_potential:
        selectedLead.lead_potential || "Warm",
      quantity:
        selectedLead.quantity || "",
      city:
        selectedLead.city || "",
      next_follow_up_date:
        selectedLead.next_follow_up_date || "",
      notes:
        selectedLead.notes || "",
      ai_summary:
        selectedLead.ai_summary || "",
    });

    setIsEditing(true);
  };

  const closeDetails = () => {
    setSelectedLead(null);
    setIsEditing(false);
    setSelectedFile(null);
    setCallStatus("");
  };

  return (
    <div className="app">

      <header className="header">

        <div>
          <h1>Sales AI Copilot</h1>
          <p>AI-powered lead management</p>
        </div>

        <button
          className="add-button"
          onClick={() => {
            setFormData(emptyForm);
            setShowForm(true);
          }}
        >
          + Add Lead
        </button>

      </header>

      <main className="container">

        <div className="page-title">
          <div>
            <h2>Leads</h2>
            <p>
              Manage and track your sales opportunities
            </p>
          </div>
        </div>


        {/* ADD NEW LEAD MODAL */}

        {showForm && (
          <div className="modal-overlay">

            <div className="modal">

              <div className="modal-header">

                <h2>Add New Lead</h2>

                <button
                  className="close-button"
                  onClick={() => setShowForm(false)}
                >
                  ×
                </button>

              </div>


              <form onSubmit={handleSubmit}>

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
                      <option value="">
                        Select Product
                      </option>

                      <option value="Polyhex">
                        Polyhex
                      </option>

                      <option value="Checks Mesh">
                        Checks Mesh
                      </option>

                      <option value="Trinity Fence Pole">
                        Trinity Fence Pole
                      </option>

                      <option value="Lato Fence">
                        Lato Fence
                      </option>

                      <option value="Privezy Wall">
                        Privezy Wall
                      </option>

                      <option value="Plant Wire">
                        Plant Wire
                      </option>

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
                      <option value="">
                        Select
                      </option>

                      <option value="B2B">
                        B2B
                      </option>

                      <option value="B2C">
                        B2C
                      </option>

                      <option value="Dealer">
                        Dealer
                      </option>

                    </select>
                  </div>


                  <div className="form-group">
                    <label>Language</label>

                    <select
                      name="language"
                      value={formData.language}
                      onChange={handleChange}
                    >
                      <option value="">
                        Select Language
                      </option>

                      <option value="English">
                        English
                      </option>

                      <option value="Tamil">
                        Tamil
                      </option>

                      <option value="Telugu">
                        Telugu
                      </option>

                      <option value="Kannada">
                        Kannada
                      </option>

                      <option value="Malayalam">
                        Malayalam
                      </option>

                      <option value="Hindi">
                        Hindi
                      </option>

                    </select>
                  </div>


                  <div className="form-group">
                    <label>Lead Potential</label>

                    <select
                      name="lead_potential"
                      value={formData.lead_potential}
                      onChange={handleChange}
                    >
                      <option value="Hot">
                        Hot
                      </option>

                      <option value="Warm">
                        Warm
                      </option>

                      <option value="Cold">
                        Cold
                      </option>

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


                <div className="form-actions">

                  <button
                    type="button"
                    className="cancel-button"
                    onClick={() => setShowForm(false)}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="save-button"
                  >
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
                    }}
                  >

                    <td>
                      {lead.customer_name}
                    </td>

                    <td>
                      {lead.phone}
                    </td>

                    <td>
                      {lead.product || "-"}
                    </td>

                    <td>
                      {lead.city || "-"}
                    </td>

                    <td>

                      <span
                        className={`badge ${lead.lead_potential?.toLowerCase()}`}
                      >
                        {lead.lead_potential || "NA"}
                      </span>

                    </td>

                    <td>
                      {lead.next_follow_up_date || "-"}
                    </td>

                  </tr>

                ))

              ) : (

                <tr>

                  <td
                    colSpan="6"
                    className="empty"
                  >
                    No leads found
                  </td>

                </tr>

              )}

            </tbody>

          </table>

        </div>


        {/* LEAD DETAILS MODAL */}

        {selectedLead && (

          <div
            className="modal-overlay"
            onClick={closeDetails}
          >

            <div
              className="modal details-modal"
              onClick={(e) => e.stopPropagation()}
            >


              <div className="modal-header">

                <div>

                  <h2>
                    {selectedLead.customer_name}
                  </h2>

                  <p className="lead-id">
                    Lead #{selectedLead.id}
                  </p>

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
                        <option value="">
                          Select Product
                        </option>

                        <option value="Polyhex">
                          Polyhex
                        </option>

                        <option value="Checks Mesh">
                          Checks Mesh
                        </option>

                        <option value="Trinity Fence Pole">
                          Trinity Fence Pole
                        </option>

                        <option value="Lato Fence">
                          Lato Fence
                        </option>

                        <option value="Privezy Wall">
                          Privezy Wall
                        </option>

                        <option value="Plant Wire">
                          Plant Wire
                        </option>

                      </select>
                    </div>


                    <div className="form-group">
                      <label>Quantity</label>

                      <input
                        name="quantity"
                        value={formData.quantity}
                        onChange={handleChange}
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
                        <option value="">
                          Select
                        </option>

                        <option value="B2B">
                          B2B
                        </option>

                        <option value="B2C">
                          B2C
                        </option>

                        <option value="Dealer">
                          Dealer
                        </option>

                      </select>
                    </div>


                    <div className="form-group">
                      <label>Language</label>

                      <select
                        name="language"
                        value={formData.language}
                        onChange={handleChange}
                      >
                        <option value="">
                          Select Language
                        </option>

                        <option value="English">
                          English
                        </option>

                        <option value="Tamil">
                          Tamil
                        </option>

                        <option value="Telugu">
                          Telugu
                        </option>

                        <option value="Kannada">
                          Kannada
                        </option>

                        <option value="Malayalam">
                          Malayalam
                        </option>

                        <option value="Hindi">
                          Hindi
                        </option>

                      </select>
                    </div>


                    <div className="form-group">
                      <label>Lead Potential</label>

                      <select
                        name="lead_potential"
                        value={formData.lead_potential}
                        onChange={handleChange}
                      >
                        <option value="Hot">
                          Hot
                        </option>

                        <option value="Warm">
                          Warm
                        </option>

                        <option value="Cold">
                          Cold
                        </option>

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


                  <div className="form-actions">

                    <button
                      type="button"
                      className="cancel-button"
                      onClick={() => setIsEditing(false)}
                    >
                      Cancel
                    </button>

                    <button
                      type="submit"
                      className="save-button"
                    >
                      Update Lead
                    </button>

                  </div>

                </form>


              ) : (

                /* VIEW MODE */

                <>

                  <div className="details-grid">

                    <div className="detail-item">
                      <span>Phone</span>
                      <strong>
                        {selectedLead.phone || "-"}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Product</span>
                      <strong>
                        {selectedLead.product || "-"}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Quantity</span>
                      <strong>
                        {selectedLead.quantity || "-"}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>City</span>
                      <strong>
                        {selectedLead.city || "-"}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Customer Category</span>
                      <strong>
                        {selectedLead.customer_category || "-"}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Language</span>
                      <strong>
                        {selectedLead.language || "-"}
                      </strong>
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

                    <p>
                      {selectedLead.notes || "-"}
                    </p>

                  </div>


                  <div className="detail-section">

                    <span>AI Summary</span>

                    <p>
                      {selectedLead.ai_summary || "-"}
                    </p>

                  </div>


                  {/* AI CALL ANALYSIS */}

                  <div className="call-upload-section">

                    <h3>AI Call Analysis</h3>

                    <p className="call-upload-description">
                      Upload a sales call recording and let AI
                      extract customer details automatically.
                    </p>

                    <input
                      type="file"
                      accept="audio/*"
                      onChange={(e) => {
                        setSelectedFile(e.target.files[0]);
                        setCallStatus("");
                      }}
                    />

                    {selectedFile && (

                      <p className="selected-file">
                        Selected: {selectedFile.name}
                      </p>

                    )}

                    <button
                      className="analyze-call-button"
                      onClick={handleCallProcessing}
                      disabled={isProcessingCall}
                    >
                      {isProcessingCall
                        ? "Processing..."
                        : "Analyze Call with AI"}
                    </button>

                    {callStatus && (

                      <p className="call-status">
                        {callStatus}
                      </p>

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