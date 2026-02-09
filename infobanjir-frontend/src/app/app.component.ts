import { Component, ElementRef, ViewChild } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { NgFor, NgIf } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule, NgIf, NgFor],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  question = '';
  loading = false;
  private loadingTimer?: ReturnType<typeof setTimeout>;
  errorMsg = '';
  result?: AskResponseData;
  messages: ChatMessage[] = [];
  @ViewChild('chatContainer') chatContainer?: ElementRef<HTMLDivElement>;
  private revealTimer?: ReturnType<typeof setTimeout>;

  private readonly apiUrl = 'http://localhost:8081/api/ask';

  constructor(private readonly http: HttpClient) {}

  submit(): void {
    const trimmed = this.question.trim();
    if (!trimmed || this.loading) {
      return;
    }
    // Append user message immediately for a chat-first UX.
    this.messages = [
      ...this.messages,
      { role: 'user', content: trimmed, timestamp: new Date().toISOString() }
    ];
    this.loading = false;
    if (this.loadingTimer) {
      clearTimeout(this.loadingTimer);
    }
    this.loadingTimer = setTimeout(() => {
      this.loading = true;
    }, 250);
    this.errorMsg = '';
    this.result = undefined;

    this.http.post<ApiResponse<AskResponseData>>(this.apiUrl, { question: trimmed }).subscribe({
      next: (response) => {
        this.result = response.data;
        const message: ChatMessage = {
          role: 'assistant',
          content: '',
          meta: {
            mode: response.data.mode,
            confidence: response.data.confidence,
            latencyMs: response.data.latencyMs
          },
          timestamp: response.data.timestamp
        };
        this.messages = [...this.messages, message];
        this.revealWithPulse(message, response.data.answer);
        this.loading = false;
        this.scrollToBottom();
        if (this.loadingTimer) {
          clearTimeout(this.loadingTimer);
          this.loadingTimer = undefined;
        }
      },
      error: () => {
        this.errorMsg = 'Request failed. Check that the API is running on port 8081.';
        this.messages = [
          ...this.messages,
          {
            role: 'assistant',
            content: 'Request failed. Please try again.',
            timestamp: new Date().toISOString()
          }
        ];
        this.loading = false;
        this.scrollToBottom();
        if (this.loadingTimer) {
          clearTimeout(this.loadingTimer);
          this.loadingTimer = undefined;
        }
      }
    });
    this.question = '';
  }

  setQuestion(sample: string): void {
    this.question = sample;
  }

  private scrollToBottom(): void {
    // Keep the latest exchange visible without layout jitter.
    setTimeout(() => {
      const el = this.chatContainer?.nativeElement;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    }, 0);
  }

  private revealWithPulse(target: ChatMessage, fullText: string): void {
    // Smooth "Codex-style" reveal without per-character typing.
    if (this.revealTimer) {
      clearTimeout(this.revealTimer);
    }
    target.content = '';
    target.meta = target.meta;
    target.revealing = true;
    this.revealTimer = setTimeout(() => {
      target.content = fullText;
      target.revealing = false;
      this.scrollToBottom();
    }, 320);
  }
}

interface AskResponseData {
  answer: string;
  mode: string;
  confidence: number;
  latencyMs: number;
  requestId: string;
  timestamp: string;
}

interface ApiResponse<T> {
  status: string;
  data: T;
  timeStamp: string;
  requestId: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  meta?: {
    mode: string;
    confidence: number;
    latencyMs: number;
  };
  revealing?: boolean;
}
