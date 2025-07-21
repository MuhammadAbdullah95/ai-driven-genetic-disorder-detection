// ... existing code ...
                {expandedId === report.id && (
                  <div className="mt-6 border-t border-medical-200 dark:border-bluegray-700 pt-6 animate-fade-in">
                    <div className="font-semibold text-medical-700 dark:text-medical-200 mb-2">Full Report:</div>
                    <div className="prose dark:prose-invert max-w-none">
                      {summaryMsg && summaryMsg.content
                        ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{summaryMsg.content}</ReactMarkdown>
                        : <span className="text-bluegray-400 italic">No report content available.</span>
                      }
                    </div>
                  </div>
                )}
// ... existing code ...
