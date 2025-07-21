"use client";

import { useState } from "react";
import api from "@/lib/api";
import { BloodReportAnalysisResponse } from "@/types/api";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import React, { useRef } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import html2canvas from "html2canvas";
import { marked } from "marked";
import Button from "@/components/ui/Button";

export default function BloodReportAnalyzerPage() {
  const [file, setFile] = useState<File | null>(null);
  const [chatTitle, setChatTitle] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BloodReportAnalysisResponse | null>(null);
  const [showNotification, setShowNotification] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!file) {
      setError("Please upload a blood report file.");
      return;
    }
    if (!chatTitle.trim()) {
      setError("Please enter a patient name or chat title.");
      return;
    }
    setLoading(true);
    try {
      const res = await api.analyzeBloodReport(file, note, chatTitle);
      setResult(res);
      setShowNotification(true);
      setTimeout(() => setShowNotification(false), 3500);
      setTimeout(() => {
        if (resultRef.current) {
          resultRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 300);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Failed to analyze blood report");
    } finally {
      setLoading(false);
    }
  };

  // Download handler
  const handleDownload = () => {
    if (!result) return;
    let content = '';
    content += 'Blood Report Analysis\n';
    content += '====================\n\n';
    content += 'Summary & Interpretation:\n';
    content += result.summary_text + '\n\n';
    content += 'Structured Data:\n';
    content += JSON.stringify(result.structured_data, null, 2) + '\n\n';
    content += 'Interpretation:\n';
    content += result.interpretation + '\n';
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (chatTitle ? chatTitle.replace(/\s+/g, '_') : 'blood_report') + '_analysis.txt';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 0);
  };

  // PDF Download handler (markdown rendering)
  const handleDownloadPDF = async () => {
    if (!result) return;
    // Combine all markdown sections
    let markdownContent = `# Blood Report Analysis\n\n`;
    markdownContent += `## Summary & Interpretation\n`;
    markdownContent += result.summary_text + '\n\n';
    markdownContent += `## Structured Data\n`;
    if (result.structured_data && typeof result.structured_data === 'object') {
      Object.entries(result.structured_data).forEach(([key, value]) => {
        if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object') {
          // Table
          const headers = Object.keys(value[0]);
          markdownContent += `\n| ${headers.join(' | ')} |\n| ${headers.map(() => '---').join(' | ')} |\n`;
          value.forEach(row => {
            markdownContent += `| ${headers.map(h => row[h]).join(' | ')} |\n`;
          });
        } else if (Array.isArray(value)) {
          markdownContent += `- **${key.replace(/_/g, ' ')}:** ${value.join(', ')}\n`;
        } else {
          markdownContent += `- **${key.replace(/_/g, ' ')}:** ${String(value)}\n`;
        }
      });
    }
    markdownContent += `\n## Medical Interpretation\n`;
    markdownContent += result.interpretation + '\n';
    // Convert markdown to HTML
    let htmlContent = '';
    try {
      htmlContent = await marked.parse(markdownContent);
    } catch (e) {
      htmlContent = '<h1>Hello PDF</h1><p>This is a test.</p>';
    }
    // Create a hidden div to render the HTML for html2canvas
    const hiddenDiv = document.createElement('div');
    hiddenDiv.innerHTML = htmlContent;
    hiddenDiv.style.position = 'fixed';
    hiddenDiv.style.left = '-9999px';
    hiddenDiv.style.top = '0';
    hiddenDiv.style.background = '#fff';
    hiddenDiv.style.color = '#222';
    hiddenDiv.style.padding = '40px 48px';
    hiddenDiv.style.width = '700px';
    hiddenDiv.style.minHeight = '800px';
    hiddenDiv.style.minWidth = '600px';
    hiddenDiv.style.fontFamily = 'Nunito, Quicksand, Inter, Arial, sans-serif';
    hiddenDiv.style.borderRadius = '18px';
    hiddenDiv.style.boxShadow = '0 4px 24px rgba(0,0,0,0.08)';
    hiddenDiv.style.lineHeight = '1.7';
    hiddenDiv.style.fontSize = '18px';
    // Add custom CSS for markdown
    const style = document.createElement('style');
    style.innerHTML = `
      h1 { font-size: 2.2em; margin-bottom: 0.5em; color: #b91c1c; font-weight: bold; }
      h2 { font-size: 1.5em; margin-top: 1.5em; margin-bottom: 0.5em; color: #991b1b; font-weight: bold; }
      h3 { font-size: 1.2em; margin-top: 1.2em; margin-bottom: 0.4em; color: #334155; font-weight: 600; }
      p { margin-bottom: 1em; }
      ul, ol { margin-left: 1.5em; margin-bottom: 1em; }
      li { margin-bottom: 0.3em; }
      table { border-collapse: collapse; width: 100%; margin-bottom: 1.5em; }
      th, td { border: 1px solid #e5e7eb; padding: 8px 12px; text-align: left; }
      th { background: #fef2f2; color: #b91c1c; font-weight: bold; }
      tr:nth-child(even) { background: #f9fafb; }
      code { background: #f3f4f6; color: #be123c; padding: 2px 6px; border-radius: 4px; font-size: 0.95em; }
      strong { color: #b91c1c; }
      em { color: #475569; }
    `;
    hiddenDiv.prepend(style);
    // Remove per-element background styling (fix overlapping)
    // (No loop over child elements)
    document.body.appendChild(hiddenDiv);
    // Use html2canvas to render the div to a canvas
    const canvas = await html2canvas(hiddenDiv, { scale: 2 });
    document.body.removeChild(hiddenDiv);
    const pdf = new jsPDF({ orientation: 'p', unit: 'pt', format: 'a4' });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const headerHeight = 32; // px space for header
    const footerHeight = 28; // px space for footer
    const margin = 20;
    const pageBreakMargin = 16; // px, extra white space at bottom of each page
    const imgWidth = pageWidth - margin * 2;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    // Calculate the height of one PDF page in canvas pixels, minus the break margin and header/footer
    const pageCanvasHeight = Math.floor((pageHeight - margin * 2 - pageBreakMargin - headerHeight - footerHeight) * (canvas.width / imgWidth));
    let renderedHeight = 0;
    let pageNum = 0;
    let totalPages = Math.ceil(canvas.height / pageCanvasHeight);
    const overlap = 20; // px, overlap between slices to prevent missing text
    while (renderedHeight < canvas.height) {
      // Create a temp canvas for the current page, add extra height for page break margin
      const sliceHeight = Math.min(pageCanvasHeight, canvas.height - renderedHeight);
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = sliceHeight + pageBreakMargin;
      const ctx = pageCanvas.getContext('2d');
      if (ctx) {
        // Fill background white (for the margin area)
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);
        // Draw the content slice
        ctx.drawImage(
          canvas,
          0,
          renderedHeight,
          canvas.width,
          sliceHeight,
          0,
          0,
          canvas.width,
          sliceHeight
        );
      }
      const imgData = pageCanvas.toDataURL('image/png');
      const pageImgHeight = (pageCanvas.height * imgWidth) / canvas.width;
      if (pageNum > 0) pdf.addPage();
      // Draw header
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(15);
      pdf.text('Blood Report Analysis', margin, margin + 10);
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(11);
      if (chatTitle) {
        pdf.text(`Patient: ${chatTitle}`, margin, margin + 26);
      }
      // Draw image below header
      const imageY = margin + headerHeight;
      pdf.addImage(imgData, 'PNG', margin, imageY, imgWidth, pageImgHeight);
      // Draw footer (page number)
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(10);
      const pageLabel = `Page ${pageNum + 1} of ${totalPages}`;
      pdf.text(pageLabel, pageWidth - margin - pdf.getTextWidth(pageLabel), pageHeight - margin - 4);
      // Overlap slices to prevent missing text
      renderedHeight += pageCanvasHeight - overlap;
      pageNum++;
    }
    pdf.save((chatTitle ? chatTitle.replace(/\s+/g, '_') : 'blood_report') + '_analysis.pdf');
  };

  return (
    <div className="max-w-xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold mb-6 text-red-700 flex items-center gap-2">
        <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3C12 3 7 8.5 7 13a5 5 0 0010 0c0-4.5-5-10-5-10z" />
          <circle cx="12" cy="17" r="2" fill="currentColor" />
        </svg>
        Blood Report Analyzer
      </h1>
      <form onSubmit={handleSubmit} className="bg-white dark:bg-bluegray-900 rounded-xl shadow-lg p-8 space-y-6">
        <div>
          <label className="block font-medium mb-1">Patient Name (Chat Title) <span className="text-red-500">*</span></label>
          <input
            type="text"
            value={chatTitle}
            onChange={e => setChatTitle(e.target.value)}
            className="block w-full border border-medical-200 rounded-lg px-3 py-2 bg-medical-50 dark:bg-bluegray-800 text-bluegray-900 dark:text-bluegray-100"
            placeholder="Enter patient name or custom chat title..."
            disabled={loading}
            required
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Upload Blood Report Image or PDF <span className="text-red-500">*</span></label>
          <input
            type="file"
            accept="image/*,application/pdf"
            onChange={e => setFile(e.target.files?.[0] || null)}
            className="block w-full border border-medical-200 rounded-lg px-3 py-2 bg-medical-50 dark:bg-bluegray-800 text-bluegray-900 dark:text-bluegray-100"
            disabled={loading}
            required
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Optional Description</label>
          <textarea
            value={note}
            onChange={e => setNote(e.target.value)}
            className="block w-full border border-medical-200 rounded-lg px-3 py-2 bg-medical-50 dark:bg-bluegray-800 text-bluegray-900 dark:text-bluegray-100"
            rows={3}
            placeholder="Add any notes or context for the analysis..."
            disabled={loading}
          />
        </div>
        {error && <div className="text-red-600 font-medium">{error}</div>}
        <button
          type="submit"
          className="w-full py-3 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold text-lg transition disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "Analyzing..." : "Analyze Blood Report"}
        </button>
      </form>
      {showNotification && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 bg-green-600 text-white px-6 py-3 rounded-xl shadow-lg z-50 text-lg font-semibold animate-fade-in">
          Blood report analysis complete! See the answer below.
        </div>
      )}
      {result && (
        <div ref={resultRef} className="mt-10 bg-medical-50 dark:bg-bluegray-800 rounded-xl shadow p-6">
          <div className="flex justify-end mb-4">
            <Button
              variant="primary"
              size="md"
              onClick={handleDownloadPDF}
              className="flex items-center gap-2"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
              Download PDF
            </Button>
          </div>
          <h2 className="text-xl font-bold mb-3 text-red-700">Analysis Result</h2>
          <div className="mb-4">
            <div className="font-semibold mb-1">Summary & Interpretation:</div>
            <div className="prose dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.summary_text}</ReactMarkdown>
            </div>
          </div>
          <div className="mb-4">
            <div className="font-semibold mb-1">Structured Data:</div>
            {result.structured_data && typeof result.structured_data === 'object' && !Array.isArray(result.structured_data) ? (
              <div className="space-y-2">
                {Object.entries(result.structured_data).map(([key, value]) => (
                  <div key={key}>
                    <span className="font-semibold capitalize">{key.replace(/_/g, ' ')}:</span>{' '}
                    {Array.isArray(value) ? (
                      value.length > 0 && typeof value[0] === 'object' ? (
                        <table className="w-full border-collapse border border-medical-300 dark:border-medical-700 my-2 text-sm">
                          <thead>
                            <tr>
                              {Object.keys(value[0]).map((col) => (
                                <th key={col} className="bg-medical-100 dark:bg-bluegray-800 text-medical-700 dark:text-medical-200 border border-medical-300 dark:border-medical-700 px-2 py-1 font-semibold">{col.replace(/_/g, ' ')}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {value.map((row, i) => (
                              <tr key={i}>
                                {Object.values(row).map((cell, j) => (
                                  <td key={j} className="border border-medical-200 dark:border-medical-700 px-2 py-1">{String(cell)}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <ul className="list-disc list-inside ml-4">
                          {value.map((item, i) => (
                            <li key={i}>{String(item)}</li>
                          ))}
                        </ul>
                      )
                    ) : (
                      <span className="ml-1">{String(value)}</span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="italic text-bluegray-400">No structured data extracted.</div>
            )}
          </div>
          <div>
            <div className="font-semibold mb-1">Interpretation:</div>
            <div className="prose dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.interpretation}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 