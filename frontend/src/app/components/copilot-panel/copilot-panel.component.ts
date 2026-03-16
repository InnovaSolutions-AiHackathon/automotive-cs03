import { Component, Input, OnInit } from '@angular/core';
import { CommonModule, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

interface Message {
  role: 'user' | 'agent';
  content: string;
  tools?: { tool: string }[];
}

@Component({
  selector: 'app-copilot-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, JsonPipe],
  templateUrl: './copilot-panel.component.html',
  styleUrls: ['./copilot-panel.component.scss']
})
export class CopilotPanelComponent {
  @Input() vehicleId = 'VH001';

  messages: Message[] = [];
  inputText = '';
  loading = false;
  imageBase64: string | null = null;
  sessionId = `sess_${Date.now()}`;

  constructor(private api: ApiService) {}

  onImageSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      this.imageBase64 = (reader.result as string).split(',')[1];
    };
    reader.readAsDataURL(file);
  }

  send(): void {
    if (!this.inputText.trim() || this.loading) return;
    this.messages.push({ role: 'user', content: this.inputText });
    this.loading = true;

    this.api.askAgent({
      session_id: this.sessionId,
      message: this.inputText,
      vehicle_id: this.vehicleId,
      image_base64: this.imageBase64 ?? undefined
    }).subscribe({
      next: (res) => {
        this.messages.push({
          role: 'agent',
          content: res.response,
          tools: res.tools_used
        });
        this.loading = false;
        this.inputText = '';
        this.imageBase64 = null;
      },
      error: () => { this.loading = false; }
    });
  }

  onEnter(event: KeyboardEvent): void {
    if (event.key === 'Enter') this.send();
  }
}