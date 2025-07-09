import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X } from 'lucide-react';
import { cn, validateVCFFile, formatFileSize } from '@/lib/utils';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  onFileRemove: () => void;
  selectedFile: File | null;
  className?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelect,
  onFileRemove,
  selectedFile,
  className,
}) => {
  const [error, setError] = useState<string>('');

  const onDrop = useCallback((acceptedFiles: File[], fileRejections: any[]) => {
    setError('');
    if (fileRejections.length > 0) {
      const rejection = fileRejections[0];
      if (rejection.errors[0].code === 'file-invalid-type') {
        setError('Please select a valid VCF file (.vcf or .vcf.gz)');
      } else if (rejection.errors[0].code === 'file-too-large') {
        setError('File size must be less than 100MB');
      } else {
        setError(rejection.errors[0].message);
      }
      return;
    }
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    if (!validateVCFFile(file)) {
      setError('Please select a valid VCF file (.vcf or .vcf.gz)');
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      setError('File size must be less than 100MB');
      return;
    }
    if (file.size === 0) {
      setError('File is empty. Please select a valid VCF file.');
      return;
    }
    onFileSelect(file);
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/vcf': ['.vcf'],
      'application/gzip': ['.vcf.gz'],
      'application/x-gzip': ['.vcf.gz']
    },
    multiple: false,
    maxSize: 100 * 1024 * 1024,
    noClick: false,
    noKeyboard: true,
  });

  const handleRemove = () => {
    setError('');
    onFileRemove();
  };

  return (
    <div className={cn('flex items-center', className)}>
      {!selectedFile ? (
        <div {...getRootProps()} className="relative">
          <input {...getInputProps()} />
          <button
            type="button"
            className={cn(
              'p-2 rounded-full bg-medical-100 dark:bg-bluegray-800 hover:bg-medical-200 dark:hover:bg-bluegray-700 text-medical-700 dark:text-medical-200 transition flex items-center justify-center shadow',
              isDragActive && 'ring-2 ring-medical-400',
              'focus:outline-none focus:ring-2 focus:ring-medical-400',
            )}
            tabIndex={-1}
            aria-label="Upload VCF file"
          >
            {/* DNA SVG Icon */}
            <span className="inline-block w-5 h-5 mr-1">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <ellipse cx="12" cy="12" rx="10" ry="10" fill="#26b6cf" fillOpacity="0.18" />
                <path d="M8 18c4-4 4-7 0-12M16 6c-4 4-4 7 0 12" stroke="#009eb2" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M9.5 15c1.5-1.5 4.5-1.5 6 0" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M14.5 9c-1.5 1.5-4.5 1.5-6 0" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </span>
            <Upload className="h-5 w-5" />
          </button>
          <span className="absolute left-1/2 -translate-x-1/2 mt-2 text-xs bg-medical-100 dark:bg-bluegray-800 text-medical-700 dark:text-medical-200 px-2 py-1 rounded shadow opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10 whitespace-nowrap">
            Upload VCF
          </span>
        </div>
      ) : (
        <div className="flex items-center bg-medical-100 dark:bg-bluegray-800 text-medical-700 dark:text-medical-200 rounded-full px-3 py-1 mr-2 text-xs max-w-xs shadow">
          <span className="truncate max-w-[100px]">{selectedFile.name}</span>
          <button
            type="button"
            onClick={handleRemove}
            className="ml-2 p-1 rounded-full hover:bg-medical-200 dark:hover:bg-bluegray-700 text-medical-400 dark:text-medical-200 hover:text-medical-700 dark:hover:text-medical-100 transition"
            aria-label="Remove file"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      {error && (
        <span className="ml-2 text-xs text-alert-500">{error}</span>
      )}
    </div>
  );
};

export default FileUpload;