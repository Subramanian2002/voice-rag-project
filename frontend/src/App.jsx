import { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  // =========================================================
  // BACKEND
  // =========================================================

  const BACKEND_URL = "http://127.0.0.1:8000";


  // =========================================================
  // SOURCE STATE
  // =========================================================

  // Selected files
  const [files, setFiles] = useState([]);

  // Current URL in the URL field
  const [url, setUrl] = useState("");

  // Successfully added URLs
  const [urls, setUrls] = useState([]);

  // Source status
  const [sourceMessage, setSourceMessage] = useState("");


  // =========================================================
  // VOICE STATE
  // =========================================================

  const [isRecording, setIsRecording] = useState(false);

  const [voiceStatus, setVoiceStatus] = useState(
    "Click the microphone and ask your question."
  );


  // =========================================================
  // CONVERSATION
  // =========================================================

  const [conversation, setConversation] = useState([]);


  // =========================================================
  // REFERENCES
  // =========================================================

  const fileInputRef = useRef(null);

  const urlInputRef = useRef(null);

  const audioContextRef = useRef(null);

  const streamRef = useRef(null);

  const microphoneSourceRef = useRef(null);

  const processorRef = useRef(null);

  const silentGainRef = useRef(null);

  const audioChunksRef = useRef([]);

  const sampleRateRef = useRef(48000);

  const silenceStartRef = useRef(null);

  const stoppingRef = useRef(false);

  const ttsAudioRef = useRef(null);

  const chatEndRef = useRef(null);


  // =========================================================
  // AUTO SCROLL CHAT
  // =========================================================

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [conversation]);


  // =========================================================
  // STOP TTS
  // =========================================================

  const stopSpeaking = () => {
    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause();
      ttsAudioRef.current.currentTime = 0;
      ttsAudioRef.current = null;
    }
  };


  // =========================================================
  // FILE SELECTION
  // =========================================================

  const handleFileSelection = (event) => {
    const selectedFiles = Array.from(
      event.target.files || []
    );

    if (selectedFiles.length === 0) {
      return;
    }

    setFiles((previousFiles) => {
      // Existing filenames
      const existingNames = new Set(
        previousFiles.map(
          (file) => file.name
        )
      );

      const newFiles = [];

      const duplicateFiles = [];


      // -------------------------------------------------------
      // Check every selected file
      // -------------------------------------------------------

      selectedFiles.forEach((file) => {
        if (existingNames.has(file.name)) {

          duplicateFiles.push(
            file.name
          );

        } else {

          newFiles.push(file);

          // Add immediately to the Set so that
          // duplicate files within the SAME
          // selection are also detected.
          existingNames.add(
            file.name
          );
        }
      });


      // -------------------------------------------------------
      // Display status message
      // -------------------------------------------------------

      if (
        duplicateFiles.length > 0 &&
        newFiles.length === 0
      ) {

        if (
          duplicateFiles.length === 1
        ) {

          setSourceMessage(
            `"${duplicateFiles[0]}" is already present.`
          );

        } else {

          setSourceMessage(
            `${duplicateFiles.length} file(s) are already present.`
          );
        }

      } else if (
        duplicateFiles.length > 0 &&
        newFiles.length > 0
      ) {

        setSourceMessage(
          `${newFiles.length} new file(s) added. ` +
          `${duplicateFiles.length} file(s) already present.`
        );

      } else {

        setSourceMessage(
          `${newFiles.length} file(s) selected.`
        );
      }


      // -------------------------------------------------------
      // Keep old files + add only new files
      // -------------------------------------------------------

      return [
        ...previousFiles,
        ...newFiles,
      ];
    });


    // ---------------------------------------------------------
    // Reset input
    //
    // This is important because it allows the user to select
    // the same file again and receive the duplicate message.
    // ---------------------------------------------------------

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };


  // =========================================================
  // REMOVE FILE
  // =========================================================

  const removeFile = (fileName) => {
    setFiles((previousFiles) =>
      previousFiles.filter(
        (file) => file.name !== fileName
      )
    );

    setSourceMessage(
      `"${fileName}" removed.`
    );
  };


  // =========================================================
  // UPLOAD FILES
  // =========================================================

  const uploadFiles = async () => {
    if (files.length === 0) {
      setSourceMessage(
        "Please select at least one file."
      );
      return;
    }

    const formData = new FormData();

    files.forEach((file) => {
      formData.append(
        "files",
        file
      );
    });

    try {

      setSourceMessage(
        `Uploading ${files.length} file(s)...`
      );

      const response =
        await fetch(
          `${BACKEND_URL}/upload`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        setSourceMessage(
          data.detail ||
            data.error ||
            "Upload failed."
        );

        return;
      }

      setSourceMessage(
        `${files.length} file(s) uploaded successfully.`
      );

    } catch (error) {

      console.error(
        "Upload error:",
        error
      );

      setSourceMessage(
        "Could not connect to backend."
      );
    }
  };


  // =========================================================
  // URL FIELD CHANGE
  // =========================================================

  const handleUrlChange = (event) => {
    const newUrl =
      event.target.value;

    console.log(
      "URL field changed:",
      newUrl
    );

    setUrl(newUrl);
  };


  // =========================================================
  // URL PASTE
  // =========================================================

  const handleUrlPaste = (event) => {
    event.preventDefault();

    const pastedText =
      event.clipboardData.getData(
        "text"
      );

    console.log(
      "URL pasted:",
      pastedText
    );

    setUrl(pastedText);

    setTimeout(() => {

      if (urlInputRef.current) {

        urlInputRef.current.focus();

        const length =
          pastedText.length;

        urlInputRef.current.setSelectionRange(
          length,
          length
        );
      }

    }, 0);
  };


  // =========================================================
  // ADD ONE URL
  // =========================================================

  const addUrl = async () => {
    const trimmedUrl =
      url.trim();

    console.log(
      "Upload URL clicked:",
      trimmedUrl
    );


    // -------------------------------------------------------
    // Validate
    // -------------------------------------------------------

    if (!trimmedUrl) {

      setSourceMessage(
        "Please paste a URL first."
      );

      return;
    }


    // -------------------------------------------------------
    // Duplicate URL
    // -------------------------------------------------------

    if (
      urls.includes(trimmedUrl)
    ) {

      setSourceMessage(
        "This URL has already been added."
      );

      return;
    }


    try {

      setSourceMessage(
        "Scraping URL..."
      );


      // -----------------------------------------------------
      // Backend request
      // -----------------------------------------------------

      const response =
        await fetch(
          `${BACKEND_URL}/add-url`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              url: trimmedUrl,
            }),
          }
        );


      const data =
        await response.json();


      console.log(
        "Add URL response:",
        data
      );


      // -----------------------------------------------------
      // Backend error
      // -----------------------------------------------------

      if (!response.ok) {

        setSourceMessage(
          data.detail ||
            data.error ||
            "URL scraping failed."
        );

        // Keep URL in field
        return;
      }


      // -----------------------------------------------------
      // Successfully added
      // -----------------------------------------------------

      setUrls(
        (previousUrls) => [
          ...previousUrls,
          trimmedUrl,
        ]
      );


      // Clear only after success
      setUrl("");


      setSourceMessage(
        "URL scraped successfully."
      );


      // Return focus to URL field
      setTimeout(() => {
        urlInputRef.current?.focus();
      }, 0);

    } catch (error) {

      console.error(
        "Add URL error:",
        error
      );


      // Keep URL if backend fails
      setSourceMessage(
        "Could not connect to backend."
      );
    }
  };


  // =========================================================
  // REMOVE URL
  // =========================================================

  const removeUrl = (
    urlToRemove
  ) => {

    setUrls(
      (previousUrls) =>
        previousUrls.filter(
          (item) =>
            item !== urlToRemove
        )
    );

    setSourceMessage(
      "URL removed."
    );
  };


  // =========================================================
  // PROCESS SOURCES
  // =========================================================

  const processSources =
    async () => {

      try {

        setSourceMessage(
          "Processing sources..."
        );


        const response =
          await fetch(
            `${BACKEND_URL}/process`,
            {
              method: "POST",
            }
          );


        const data =
          await response.json();


        console.log(
          "Process response:",
          data
        );


        if (!response.ok) {

          setSourceMessage(
            data.detail ||
              data.error ||
              "Processing failed."
          );

          return;
        }


        setSourceMessage(
          `Processed ${data.files_processed} file(s), ` +
            `${data.urls_processed} URL(s), ` +
            `${data.chunks_stored} chunks.`
        );

      } catch (error) {

        console.error(
          "Process error:",
          error
        );

        setSourceMessage(
          "Could not connect to backend."
        );
      }
    };


  // =========================================================
  // TEXT TO SPEECH
  // =========================================================

  const speakAnswer =
    async (text) => {

      if (
        !text ||
        !text.trim()
      ) {
        return;
      }


      try {

        stopSpeaking();


        setVoiceStatus(
          "Generating voice answer..."
        );


        const response =
          await fetch(
            `${BACKEND_URL}/tts`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                text,
              }),
            }
          );


        if (!response.ok) {

          console.error(
            "TTS error:",
            await response.text()
          );

          setVoiceStatus(
            "Answer generated, but voice generation failed."
          );

          return;
        }


        const audioBlob =
          await response.blob();


        const audioUrl =
          URL.createObjectURL(
            audioBlob
          );


        const audio =
          new Audio(audioUrl);


        ttsAudioRef.current =
          audio;


        audio.onplay = () => {

          setVoiceStatus(
            "🔊 Speaking..."
          );
        };


        audio.onended = () => {

          setVoiceStatus(
            "Click the microphone and ask your next question."
          );

          ttsAudioRef.current =
            null;

          URL.revokeObjectURL(
            audioUrl
          );
        };


        audio.onerror = () => {

          setVoiceStatus(
            "Answer generated, but audio playback failed."
          );

          ttsAudioRef.current =
            null;

          URL.revokeObjectURL(
            audioUrl
          );
        };


        await audio.play();

      } catch (error) {

        console.error(
          "TTS error:",
          error
        );

        setVoiceStatus(
          "Answer generated, but voice playback failed."
        );
      }
    };


  // =========================================================
  // ASK RAG QUESTION
  // =========================================================

  const askQuestion =
    async (question) => {

      if (
        !question ||
        !question.trim()
      ) {

        setVoiceStatus(
          "I could not understand the question. Please try again."
        );

        return;
      }


      // Stop current TTS
      stopSpeaking();


      setVoiceStatus(
        "Thinking..."
      );


      try {

        const conversationHistory =
          conversation.map(
            (message) => ({
              role:
                message.role,

              content:
                message.text,
            })
          );


        console.log(
          "Question:",
          question
        );


        console.log(
          "Conversation history:",
          conversationHistory
        );


        const response =
          await fetch(
            `${BACKEND_URL}/ask`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                question,

                conversation_history:
                  conversationHistory,
              }),
            }
          );


        const data =
          await response.json();


        console.log(
          "RAG response:",
          data
        );


        if (!response.ok) {

          setVoiceStatus(
            data.detail ||
              data.error ||
              "Could not generate an answer."
          );

          return;
        }


        const generatedAnswer =
          data.answer || "";


        const generatedSources =
          data.sources || [];


        // Add question + answer
        setConversation(
          (previousConversation) => [
            ...previousConversation,

            {
              role: "user",

              text: question,
            },

            {
              role: "assistant",

              text:
                generatedAnswer,

              sources:
                generatedSources,
            },
          ]
        );


        // Speak answer
        if (
          generatedAnswer.trim()
        ) {

          await speakAnswer(
            generatedAnswer
          );

        } else {

          setVoiceStatus(
            "No answer was generated."
          );
        }

      } catch (error) {

        console.error(
          "Ask error:",
          error
        );

        setVoiceStatus(
          "Could not connect to the backend."
        );
      }
    };


  // =========================================================
  // FLOAT32 → 16 BIT PCM
  // =========================================================

  const floatTo16BitPCM =
    (float32Array) => {

      const output =
        new Int16Array(
          float32Array.length
        );


      for (
        let i = 0;
        i < float32Array.length;
        i++
      ) {

        const sample =
          Math.max(
            -1,
            Math.min(
              1,
              float32Array[i]
            )
          );


        if (
          sample < 0
        ) {

          output[i] =
            sample * 0x8000;

        } else {

          output[i] =
            sample * 0x7fff;
        }
      }


      return output;
    };


  // =========================================================
  // DOWNSAMPLE AUDIO
  // =========================================================

  const downsampleAudio =
    (
      audioData,
      inputSampleRate,
      outputSampleRate
    ) => {

      if (
        outputSampleRate >=
        inputSampleRate
      ) {
        return audioData;
      }


      const ratio =
        inputSampleRate /
        outputSampleRate;


      const newLength =
        Math.round(
          audioData.length /
            ratio
        );


      const result =
        new Float32Array(
          newLength
        );


      let offsetResult = 0;

      let offsetBuffer = 0;


      while (
        offsetResult <
        result.length
      ) {

        const nextOffsetBuffer =
          Math.round(
            (offsetResult + 1) *
              ratio
          );


        let accum = 0;

        let count = 0;


        for (
          let i = offsetBuffer;

          i < nextOffsetBuffer &&
          i < audioData.length;

          i++
        ) {

          accum +=
            audioData[i];

          count++;
        }


        result[
          offsetResult
        ] =
          count > 0
            ? accum / count
            : 0;


        offsetResult++;

        offsetBuffer =
          nextOffsetBuffer;
      }


      return result;
    };


  // =========================================================
  // CREATE WAV
  // =========================================================

  const createWavBlob =
    (
      audioData,
      sampleRate
    ) => {

      const targetSampleRate =
        16000;


      const downsampled =
        downsampleAudio(
          audioData,
          sampleRate,
          targetSampleRate
        );


      const pcmData =
        floatTo16BitPCM(
          downsampled
        );


      const buffer =
        new ArrayBuffer(
          44 +
            pcmData.length * 2
        );


      const view =
        new DataView(
          buffer
        );


      const writeString =
        (
          offset,
          string
        ) => {

          for (
            let i = 0;
            i < string.length;
            i++
          ) {

            view.setUint8(
              offset + i,
              string.charCodeAt(i)
            );
          }
        };


      // RIFF
      writeString(
        0,
        "RIFF"
      );


      view.setUint32(
        4,
        36 +
          pcmData.length * 2,
        true
      );


      // WAVE
      writeString(
        8,
        "WAVE"
      );


      // fmt
      writeString(
        12,
        "fmt "
      );


      view.setUint32(
        16,
        16,
        true
      );


      // PCM
      view.setUint16(
        20,
        1,
        true
      );


      // Mono
      view.setUint16(
        22,
        1,
        true
      );


      // Sample rate
      view.setUint32(
        24,
        targetSampleRate,
        true
      );


      // Byte rate
      view.setUint32(
        28,
        targetSampleRate * 2,
        true
      );


      // Block align
      view.setUint16(
        32,
        2,
        true
      );


      // Bits per sample
      view.setUint16(
        34,
        16,
        true
      );


      // data
      writeString(
        36,
        "data"
      );


      view.setUint32(
        40,
        pcmData.length * 2,
        true
      );


      let offset = 44;


      for (
        let i = 0;
        i < pcmData.length;
        i++
      ) {

        view.setInt16(
          offset,
          pcmData[i],
          true
        );

        offset += 2;
      }


      return new Blob(
        [buffer],
        {
          type: "audio/wav",
        }
      );
    };


  // =========================================================
  // TRANSCRIBE AUDIO
  // =========================================================

  const transcribeAudio =
    async (audioBlob) => {

      try {

        setVoiceStatus(
          "Understanding your question..."
        );


        const formData =
          new FormData();


        formData.append(
          "audio",
          audioBlob,
          "recording.wav"
        );


        const response =
          await fetch(
            `${BACKEND_URL}/transcribe`,
            {
              method: "POST",

              body: formData,
            }
          );


        const data =
          await response.json();


        console.log(
          "Transcription response:",
          data
        );


        if (!response.ok) {

          setVoiceStatus(
            data.detail ||
              data.error ||
              "Speech recognition failed."
          );

          return;
        }


        const recognizedText =
          data.text || "";


        console.log(
          "Recognized question:",
          recognizedText
        );


        if (
          recognizedText.trim()
        ) {

          await askQuestion(
            recognizedText
          );

        } else {

          setVoiceStatus(
            "I could not understand the question. Please try again."
          );
        }

      } catch (error) {

        console.error(
          "Transcription error:",
          error
        );

        setVoiceStatus(
          "Could not connect to speech recognition."
        );
      }
    };


  // =========================================================
  // FINISH RECORDING
  // =========================================================

  const finishRecording =
    async () => {

      if (
        stoppingRef.current
      ) {
        return;
      }


      stoppingRef.current =
        true;


      setIsRecording(
        false
      );


      if (
        processorRef.current
      ) {

        processorRef.current
          .disconnect();

        processorRef.current =
          null;
      }


      if (
        microphoneSourceRef.current
      ) {

        microphoneSourceRef.current
          .disconnect();

        microphoneSourceRef.current =
          null;
      }


      if (
        silentGainRef.current
      ) {

        silentGainRef.current
          .disconnect();

        silentGainRef.current =
          null;
      }


      if (
        streamRef.current
      ) {

        streamRef.current
          .getTracks()
          .forEach(
            (track) => {
              track.stop();
            }
          );

        streamRef.current =
          null;
      }


      const chunks =
        audioChunksRef.current;


      audioChunksRef.current =
        [];


      let totalLength = 0;


      chunks.forEach(
        (chunk) => {
          totalLength +=
            chunk.length;
        }
      );


      if (
        totalLength === 0
      ) {

        setVoiceStatus(
          "No speech was recorded. Please try again."
        );


        if (
          audioContextRef.current
        ) {

          try {
            await audioContextRef.current.close();
          } catch (error) {
            console.warn(error);
          }

          audioContextRef.current =
            null;
        }


        stoppingRef.current =
          false;

        return;
      }


      const combinedAudio =
        new Float32Array(
          totalLength
        );


      let offset = 0;


      chunks.forEach(
        (chunk) => {

          combinedAudio.set(
            chunk,
            offset
          );

          offset +=
            chunk.length;
        }
      );


      const wavBlob =
        createWavBlob(
          combinedAudio,
          sampleRateRef.current
        );


      if (
        audioContextRef.current
      ) {

        try {
          await audioContextRef.current.close();
        } catch (error) {
          console.warn(error);
        }

        audioContextRef.current =
          null;
      }


      await transcribeAudio(
        wavBlob
      );


      stoppingRef.current =
        false;
    };


  // =========================================================
  // SILENCE DETECTION
  // =========================================================

  const checkSilence =
    (audioBuffer) => {

      let sum = 0;


      for (
        let i = 0;
        i < audioBuffer.length;
        i++
      ) {

        const sample =
          audioBuffer[i];

        sum +=
          sample * sample;
      }


      const rms =
        Math.sqrt(
          sum /
            audioBuffer.length
        );


      const SILENCE_THRESHOLD =
        0.015;


      if (
        rms <
        SILENCE_THRESHOLD
      ) {

        if (
          silenceStartRef.current ===
          null
        ) {

          silenceStartRef.current =
            Date.now();


          console.log(
            "Silence started..."
          );
        }


        const silenceDuration =
          Date.now() -
          silenceStartRef.current;


        const silenceSeconds =
          Math.floor(
            silenceDuration /
              1000
          );


        console.log(
          `Silence duration: ${silenceSeconds} seconds`
        );


        if (
          silenceDuration >=
          5000
        ) {

          console.log(
            "5 seconds of silence detected."
          );


          setVoiceStatus(
            "Silence detected. Processing..."
          );


          finishRecording();


          return true;
        }

      } else {

        silenceStartRef.current =
          null;
      }


      return false;
    };


  // =========================================================
  // START RECORDING
  // =========================================================

  const startRecording =
    async () => {

      try {

        // Stop current TTS
        stopSpeaking();


        setVoiceStatus(
          "Requesting microphone..."
        );


        stoppingRef.current =
          false;


        silenceStartRef.current =
          null;


        audioChunksRef.current =
          [];


        const stream =
          await navigator.mediaDevices
            .getUserMedia({
              audio: {
                channelCount: 1,

                echoCancellation:
                  true,

                noiseSuppression:
                  true,

                autoGainControl:
                  true,

                sampleRate: 48000,
              },
            });


        streamRef.current =
          stream;


        const AudioContext =
          window.AudioContext ||
          window.webkitAudioContext;


        if (!AudioContext) {

          throw new Error(
            "Web Audio API is not supported."
          );
        }


        const audioContext =
          new AudioContext();


        audioContextRef.current =
          audioContext;


        if (
          audioContext.state ===
          "suspended"
        ) {

          await audioContext.resume();
        }


        sampleRateRef.current =
          audioContext.sampleRate;


        const microphoneSource =
          audioContext
            .createMediaStreamSource(
              stream
            );


        microphoneSourceRef.current =
          microphoneSource;


        const processor =
          audioContext
            .createScriptProcessor(
              4096,
              1,
              1
            );


        processorRef.current =
          processor;


        const silentGain =
          audioContext.createGain();


        silentGain.gain.value =
          0;


        silentGainRef.current =
          silentGain;


        processor.onaudioprocess =
          (event) => {

            if (
              stoppingRef.current
            ) {
              return;
            }


            const inputData =
              event.inputBuffer
                .getChannelData(
                  0
                );


            const audioCopy =
              new Float32Array(
                inputData.length
              );


            audioCopy.set(
              inputData
            );


            audioChunksRef.current.push(
              audioCopy
            );


            checkSilence(
              inputData
            );
          };


        microphoneSource.connect(
          processor
        );


        processor.connect(
          silentGain
        );


        silentGain.connect(
          audioContext.destination
        );


        setIsRecording(
          true
        );


        setVoiceStatus(
          "🎤 Listening... Speak your question."
        );


        console.log(
          "Microphone access granted."
        );


        console.log(
          "Recording started."
        );

      } catch (error) {

        console.error(
          "Microphone error:",
          error
        );


        setIsRecording(
          false
        );


        setVoiceStatus(
          "Could not access microphone. Please allow microphone permission."
        );


        if (
          streamRef.current
        ) {

          streamRef.current
            .getTracks()
            .forEach(
              (track) => {
                track.stop();
              }
            );


          streamRef.current =
            null;
        }


        if (
          audioContextRef.current
        ) {

          try {
            await audioContextRef.current.close();
          } catch (closeError) {
            console.warn(
              closeError
            );
          }


          audioContextRef.current =
            null;
        }
      }
    };


  // =========================================================
  // MANUAL STOP
  // =========================================================

  const stopRecording =
    () => {

      silenceStartRef.current =
        null;

      finishRecording();
    };


  // =========================================================
  // UI
  // =========================================================

  return (
    <div className="app">

      {/* =====================================================
          SIDEBAR
          ===================================================== */}

      <aside className="sidebar">

        <div className="sidebar-header">

          <h2>
            🎙️ QUIRRI RAG
          </h2>

          <p>
            Knowledge Sources
          </p>

        </div>


        {/* ===================================================
            FILE UPLOAD
            =================================================== */}

        <div className="source-section">

          <h3>
            📄 Upload Files
          </h3>


          <label className="file-input">

            Choose Files

            <input
              ref={fileInputRef}

              type="file"

              multiple

              accept=".pdf,.txt,.pptx"

              onChange={
                handleFileSelection
              }
            />

          </label>


          {files.length > 0 && (

            <div className="selected-files">

              <div className="list-title">
                Selected Files
              </div>


              {files.map(
                (file, index) => (

                  <div
                    className="file-item"

                    key={
                      `${file.name}-${index}`
                    }
                  >

                    <span className="file-icon">
                      📄
                    </span>


                    <span className="file-name">
                      {file.name}
                    </span>


                    <button
                      type="button"

                      className="remove-button"

                      onClick={() =>
                        removeFile(
                          file.name
                        )
                      }

                      title="Remove file"
                    >
                      ×
                    </button>

                  </div>
                )
              )}

            </div>
          )}


          <button
            type="button"

            className="sidebar-button"

            onClick={
              uploadFiles
            }
          >
            Upload Files
          </button>

        </div>


        {/* ===================================================
            WEBSITE URL
            =================================================== */}

        <div className="source-section">

          <h3>
            🔗 Add Website
          </h3>


          <input
            ref={urlInputRef}

            className="url-input"

            type="text"

            placeholder="Paste website URL"

            value={url}

            onChange={
              handleUrlChange
            }

            onPaste={
              handleUrlPaste
            }

            onKeyDown={(event) => {

              if (
                event.key ===
                "Enter"
              ) {

                event.preventDefault();

                addUrl();
              }
            }}

            autoComplete="off"

            spellCheck="false"

            style={{
              width: "100%",

              boxSizing:
                "border-box",

              backgroundColor:
                "#ffffff",

              color:
                "#111827",

              WebkitTextFillColor:
                "#111827",

              fontSize:
                "13px",

              padding:
                "10px 11px",

              border:
                "1px solid #d1d5db",

              borderRadius:
                "8px",

              outline:
                "none",

              opacity: 1,
            }}
          />


          <button
            type="button"

            className="sidebar-button"

            onClick={
              addUrl
            }
          >
            Add URL
          </button>


          {urls.length > 0 && (

            <div className="selected-files">

              <div className="list-title">
                Added Websites
              </div>


              {urls.map(
                (item, index) => (

                  <div
                    className="file-item"

                    key={
                      `${item}-${index}`
                    }
                  >

                    <span className="file-icon">
                      🔗
                    </span>


                    <span className="file-name">
                      {item}
                    </span>


                    <button
                      type="button"

                      className="remove-button"

                      onClick={() =>
                        removeUrl(
                          item
                        )
                      }

                      title="Remove URL"
                    >
                      ×
                    </button>

                  </div>
                )
              )}

            </div>
          )}

        </div>


        {/* ===================================================
            PROCESS SOURCES
            =================================================== */}

        <div className="source-section">

          <button
            type="button"

            className="process-button"

            onClick={
              processSources
            }
          >
            ⚙️ Process Sources
          </button>

        </div>


        {/* ===================================================
            SOURCE MESSAGE
            =================================================== */}

        {sourceMessage && (

          <div className="source-message">
            {sourceMessage}
          </div>
        )}


        <div className="sidebar-footer">
          Voice-only interaction
        </div>

      </aside>


      {/* =====================================================
          MAIN CHAT
          ===================================================== */}

      <main className="main">

        <header className="chat-header">

          <div>

            <h1>
              QUIRRI RAG Assistant
            </h1>

            <p>
              Ask questions about your knowledge sources
            </p>

          </div>


          <div className="status-indicator">

            <span className="status-dot"></span>

            Ready

          </div>

        </header>


        {/* ===================================================
            CHAT AREA
            =================================================== */}

        <section className="chat-area">

          {conversation.length === 0 ? (

            <div className="welcome">

              <div className="welcome-icon">
                🎙️
              </div>


              <h2>
                How can I help you?
              </h2>


              <p>
                Upload your documents or add
                websites from the sidebar,
                then ask your question using
                your voice.
              </p>


              <div className="welcome-examples">

                <div>
                  “What is Python?”
                </div>

                <div>
                  “What are the Data types in Python?”
                </div>

              </div>

            </div>

          ) : (

            <div className="messages">

              {conversation.map(
                (message, index) => (

                  <div
                    key={index}

                    className={
                      message.role ===
                      "user"
                        ? "message user-message"
                        : "message assistant-message"
                    }
                  >

                    <div className="message-avatar">

                      {message.role ===
                      "user"
                        ? "👤"
                        : "🤖"}

                    </div>


                    <div className="message-content">

                      <div className="message-role">

                        {message.role ===
                        "user"
                          ? "You"
                          : "Assistant"}

                      </div>


                      <div className="message-text">

                        {message.text}

                      </div>


                      {message.role ===
                        "assistant" &&
                        message.sources &&
                        message.sources.length >
                          0 && (

                          <div className="message-sources">

                            <div className="sources-title">
                              Sources
                            </div>


                            {message.sources.map(
                              (
                                source,
                                sourceIndex
                              ) => (

                                <div
                                  className="source-item"

                                  key={
                                    sourceIndex
                                  }
                                >

                                  <span>
                                    📄
                                  </span>


                                  <span>
                                    {
                                      source.source_name
                                    }
                                  </span>

                                </div>
                              )
                            )}

                          </div>
                        )}

                    </div>

                  </div>
                )
              )}


              <div
                ref={chatEndRef}
              />

            </div>
          )}

        </section>


        {/* ===================================================
            VOICE AREA
            =================================================== */}

        <section className="voice-area">

          <div className="voice-status">
            {voiceStatus}
          </div>


          <button
            type="button"

            className={
              isRecording
                ? "mic-button recording"
                : "mic-button"
            }

            onClick={
              isRecording
                ? stopRecording
                : startRecording
            }

            aria-label={
              isRecording
                ? "Stop recording"
                : "Start recording"
            }
          >

            {isRecording
              ? "⏹"
              : "🎙️"}

          </button>


          <div className="voice-label">

            {isRecording
              ? "Listening..."
              : "Ask a question"}

          </div>


          {!isRecording && (

            <div className="voice-hint">

              Speak naturally. Recording
              stops after 5 seconds of silence.

            </div>

          )}

        </section>

      </main>

    </div>
  );
}

export default App;