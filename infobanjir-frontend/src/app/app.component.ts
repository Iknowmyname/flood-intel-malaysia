import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { NgFor, NgIf } from '@angular/common';
import { runtimeConfig } from './runtime-config';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule, NgIf, NgFor],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  question = '';
  loading = false;
  private loadingTimer?: ReturnType<typeof setTimeout>;
  errorMsg = '';
  result?: AskResponseData;
  messages: ChatMessage[] = [];
  @ViewChild('chatContainer') chatContainer?: ElementRef<HTMLDivElement>;
  private revealTimer?: ReturnType<typeof setTimeout>;
  starterPrompts: StarterPrompt[] = [
    { label: 'Check flood risk in my state', question: 'What is the flood risk in Selangor today?' },
    { label: 'Find highest rainfall in last 24h', question: 'Where was the highest rainfall in the last 24 hours?' },
    { label: 'Compare river levels across states', question: 'Compare current river levels across states in Malaysia.' },
    { label: 'Show stations driving flood risk', question: 'Which stations are driving flood risk in Johor today?' }
  ];
  guidedMetric: GuidedMetric = 'Flood risk';
  guidedState = 'Selangor';
  guidedTime: GuidedTime = 'Today';
  guidedAction: GuidedAction = 'Summary';
  readonly guidedMetrics: GuidedMetric[] = ['Flood risk', 'Rainfall', 'River level'];
  readonly guidedStates = [
    'Malaysia', 'Johor', 'Kedah', 'Kelantan', 'Melaka', 'Negeri Sembilan', 'Pahang',
    'Perak', 'Perlis', 'Penang', 'Sabah', 'Sarawak', 'Selangor', 'Terengganu',
    'Kuala Lumpur', 'Putrajaya', 'Labuan'
  ];
  readonly guidedTimes: GuidedTime[] = ['Today', 'Yesterday', 'Last 24 hours'];
  readonly guidedActions: GuidedAction[] = ['Summary', 'Top stations', 'Compare states'];
  quickInsights: InsightCard[] = [
    {
      title: 'Flood risk snapshot',
      query: 'What is the flood risk in Malaysia today?',
      value: 'Loading...',
      loading: true
    },
    {
      title: 'Rainfall hotspots',
      query: 'Which stations recorded the highest rainfall in Malaysia in the last 24 hours?',
      value: 'Loading...',
      loading: true
    },
    {
      title: 'River level hotspots',
      query: 'Which stations have the highest river level in Malaysia today?',
      value: 'Loading...',
      loading: true
    }
  ];

  private readonly apiUrl = runtimeConfig.apiUrl;

  constructor(private readonly http: HttpClient) {}

  ngOnInit(): void {
    this.loadQuickInsights();
  }

  submit(): void {
    const trimmed = this.question.trim();
    if (!trimmed || this.loading) {
      return;
    }
    if (this.isVagueFloodQuestion(trimmed)) {
      this.messages = [
        ...this.messages,
        { role: 'user', content: trimmed, timestamp: new Date().toISOString() },
        {
          role: 'assistant',
          content:
            'I can narrow this down for you. Ask one of these:\n' +
            '1) Flood risk in a specific state\n' +
            '2) Top rainfall stations\n' +
            '3) Top river level stations\n' +
            'I will also share a quick national snapshot now.',
          timestamp: new Date().toISOString()
        }
      ];
      this.sendQuestion('What is the flood risk in Malaysia today?', false);
      this.question = '';
      return;
    }

    this.sendQuestion(trimmed, true);
    this.question = '';
  }

  setQuestion(sample: string): void {
    this.question = sample;
  }

  buildGuidedQuestion(): void {
    const timeLabel = this.guidedTime === 'Today'
      ? 'today'
      : this.guidedTime === 'Yesterday'
        ? 'yesterday'
        : 'in the last 24 hours';

    const location = this.guidedState === 'Malaysia' ? 'Malaysia' : this.guidedState;

    if (this.guidedMetric === 'Flood risk') {
      if (this.guidedAction === 'Top stations') {
        this.question = `Which stations are driving flood risk in ${location} ${timeLabel}?`;
        return;
      }
      if (this.guidedAction === 'Compare states') {
        this.question = `Compare flood risk across states in Malaysia ${timeLabel}.`;
        return;
      }
      this.question = `What is the flood risk in ${location} ${timeLabel}?`;
      return;
    }

    if (this.guidedMetric === 'Rainfall') {
      if (this.guidedAction === 'Top stations') {
        this.question = `Which stations recorded the highest rainfall in ${location} ${timeLabel}?`;
        return;
      }
      if (this.guidedAction === 'Compare states') {
        this.question = `Compare rainfall across states in Malaysia ${timeLabel}.`;
        return;
      }
      this.question = `What is the rainfall summary in ${location} ${timeLabel}?`;
      return;
    }

    if (this.guidedAction === 'Top stations') {
      this.question = `Which stations have the highest river level in ${location} ${timeLabel}?`;
      return;
    }
    if (this.guidedAction === 'Compare states') {
      this.question = `Compare river levels across states in Malaysia ${timeLabel}.`;
      return;
    }
    this.question = `What is the river level summary in ${location} ${timeLabel}?`;
  }

  private loadQuickInsights(): void {
    this.quickInsights.forEach((card) => this.fetchQuickInsight(card));
  }

  private sendQuestion(question: string, appendUser: boolean): void {
    if (appendUser) {
      this.messages = [
        ...this.messages,
        { role: 'user', content: question, timestamp: new Date().toISOString() }
      ];
    }
    this.loading = false;
    if (this.loadingTimer) {
      clearTimeout(this.loadingTimer);
    }
    this.loadingTimer = setTimeout(() => {
      this.loading = true;
    }, 250);
    this.errorMsg = '';
    this.result = undefined;

    this.http.post<ApiResponse<AskResponseData>>(this.apiUrl, { question }).subscribe({
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
        this.errorMsg = 'Request failed. Check backend availability and API URL config.';
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
  }

  private isVagueFloodQuestion(question: string): boolean {
    const q = question.toLowerCase();
    const mentionsFlood = q.includes('flood') || q.includes('risk') || q.includes('danger');
    const hasSpecificMetric =
      q.includes('rainfall') || q.includes('river level') || q.includes('water level') || q.includes('station');
    const hasState = this.guidedStates
      .filter((state) => state !== 'Malaysia')
      .some((state) => q.includes(state.toLowerCase()));
    const isVaguePhrase =
      q.includes('how bad') || q.includes('is it bad') || q.includes('situation now') || q.includes('right now');
    return mentionsFlood && !hasSpecificMetric && !hasState && isVaguePhrase;
  }

  private fetchQuickInsight(card: InsightCard): void {
    card.loading = true;
    this.http.post<ApiResponse<AskResponseData>>(this.apiUrl, { question: card.query }).subscribe({
      next: (response) => {
        card.value = response.data.answer;
        card.loading = false;
      },
      error: () => {
        card.value = 'Unavailable right now.';
        card.loading = false;
      }
    });
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

interface StarterPrompt {
  label: string;
  question: string;
}

type GuidedMetric = 'Flood risk' | 'Rainfall' | 'River level';
type GuidedTime = 'Today' | 'Yesterday' | 'Last 24 hours';
type GuidedAction = 'Summary' | 'Top stations' | 'Compare states';

interface InsightCard {
  title: string;
  query: string;
  value: string;
  loading: boolean;
}
