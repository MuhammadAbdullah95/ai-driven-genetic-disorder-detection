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
              'p-2 rounded-full bg-gray-800 hover:bg-primary-600 text-gray-300 hover:text-white transition flex items-center justify-center',
              isDragActive && 'ring-2 ring-primary-500',
              'focus:outline-none focus:ring-2 focus:ring-primary-500',
            )}
            tabIndex={-1}
            aria-label="Upload VCF file"
          >
            <Upload className="h-5 w-5" />
          </button>
          <span className="absolute left-1/2 -translate-x-1/2 mt-2 text-xs bg-gray-900 text-gray-200 px-2 py-1 rounded shadow opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10 whitespace-nowrap">
            Upload VCF
          </span>
        </div>
      ) : (
        <div className="flex items-center bg-gray-800 text-gray-100 rounded-full px-3 py-1 mr-2 text-xs max-w-xs">
          <span className="truncate max-w-[100px]">{selectedFile.name}</span>
          <button
            type="button"
            onClick={handleRemove}
            className="ml-2 p-1 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white transition"
            aria-label="Remove file"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      {error && (
        <span className="ml-2 text-xs text-red-400">{error}</span>
      )}
    </div>
  );
};

export default FileUpload;