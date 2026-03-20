import { Component, Input, ChangeDetectorRef } from '@angular/core';
import { CommonModule, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

interface Vehicle {
  vehicle_code: string;
  make: string;
  model: string;
  year: number;
}

interface Message {
  role: 'user' | 'agent';
  content: string;
  tools?: { tool: string }[];
  vehicles?: Vehicle[];
}

@Component({
  selector: 'app-copilot-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, JsonPipe],
  templateUrl: './copilot-panel.component.html',
  styleUrls: ['./copilot-panel.component.scss']
})
export class CopilotPanelComponent {
  @Input() vehicleId!: string;

  messages: Message[] = [];
  inputText = '';
  loading = false;
  imageBase64: string | null = null;
  sessionId = `sess_${Date.now()}`;
  private _pendingMessage = '';

  constructor(
    private api: ApiService,
    private auth: AuthService,
    private cd: ChangeDetectorRef
  ) {}

  // =========================
  // 📷 IMAGE UPLOAD
  // =========================
  onImageSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      this.imageBase64 = (reader.result as string).split(',')[1];
    };
    reader.readAsDataURL(file);
  }

  // =========================
  // 🚀 SEND MESSAGE
  // =========================
  send(): void {
    if (!this.inputText.trim() || this.loading) return;

    const userMessage: Message = {
      role: 'user',
      content: this.inputText
    };

    this.messages = [...this.messages, userMessage];
    this._pendingMessage = this.inputText;
    this.loading = true;

    const payload = {
      session_id: this.sessionId,
      message: this.inputText,
      vehicle_id: this.vehicleId,
      image_base64: this.imageBase64 ?? undefined,
      user_id: this.auth.getUserId() ?? undefined
    };

    this.api.askAgent(payload).subscribe({
      next: (res: any) => {
        this.handleResponse(res);
      },
      error: () => {
        this.addAgentMessage('Something went wrong. Please try again.');
        this.loading = false;
        this.cd.detectChanges();
      }
    });

    this.inputText = '';
    this.imageBase64 = null;
  }

  // =========================
  // 🚗 VEHICLE SELECTION
  // =========================
  selectVehicle(vehicle: Vehicle): void {
    this.vehicleId = vehicle.vehicle_code;

    const userMessage: Message = {
      role: 'user',
      content: `Selected: ${vehicle.make} ${vehicle.model} (${vehicle.year})`
    };

    this.messages = [...this.messages, userMessage];
    this.loading = true;

    const payload = {
      session_id: this.sessionId,
      message: this._pendingMessage || `Show full status for vehicle ${vehicle.vehicle_code}`,
      vehicle_id: this.vehicleId
    };

    this.api.askAgent(payload).subscribe({
      next: (res: any) => {
        this.handleResponse(res);
      },
      error: () => {
        this.addAgentMessage('Failed to fetch vehicle data.');
        this.loading = false;
        this.cd.detectChanges();
      }
    });
  }

  // =========================
  // 🧠 HANDLE RESPONSE (CORE)
  // =========================
  private handleResponse(res: any): void {

    let agentMessage: Message;

    // 🔥 VEHICLE LIST RESPONSE
    if (res.data?.vehicles?.length) {
      agentMessage = {
        role: 'agent',
        content: res.response || 'Please select a vehicle',
        vehicles: res.data.vehicles
      };
    }

    // 🔥 NORMAL RESPONSE
    else {
      agentMessage = {
        role: 'agent',
        content: res.response || 'No response from server',
        tools: res.tools_used
      };
    }

    this.messages = [...this.messages, agentMessage];
    this.loading = false;

    // 🔥 force UI refresh (fix delayed rendering)
    this.cd.detectChanges();
  }

  // =========================
  // 💬 ADD AGENT MESSAGE
  // =========================
  private addAgentMessage(text: string): void {
    this.messages = [
      ...this.messages,
      { role: 'agent', content: text }
    ];
  }

  // =========================
  // ⌨️ ENTER KEY
  // =========================
  onEnter(event: KeyboardEvent): void {
    if (event.key === 'Enter') this.send();
  }

  // =========================
  // 🚫 BLOCK INPUT UNTIL SELECT
  // =========================
  get waitingForVehicle(): boolean {
    return this.messages.some(m => m.vehicles) && !this.vehicleId;
  }
}