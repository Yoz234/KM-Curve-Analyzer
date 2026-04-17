"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import clsx from "clsx";

interface Props {
  onFile: (file: File) => void;
  accept?: string;
  label?: string;
}

export default function DropZone({ onFile, accept = "image/*", label = "Drop KM curve image here" }: Props) {
  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) onFile(accepted[0]);
  }, [onFile]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: { [accept]: [] },
    multiple: false,
    maxSize: 20 * 1024 * 1024,
  });

  return (
    <div
      {...getRootProps()}
      className={clsx(
        "border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors",
        isDragActive ? "border-primary bg-blue-50" : "border-slate-300 hover:border-primary"
      )}
    >
      <input {...getInputProps()} />
      <div className="text-4xl mb-3">🖼</div>
      {acceptedFiles[0] ? (
        <p className="text-sm text-slate-700 font-medium">{acceptedFiles[0].name}</p>
      ) : (
        <>
          <p className="text-slate-600 font-medium">{label}</p>
          <p className="text-xs text-slate-400 mt-1">PNG, JPEG — max 20 MB</p>
        </>
      )}
    </div>
  );
}
