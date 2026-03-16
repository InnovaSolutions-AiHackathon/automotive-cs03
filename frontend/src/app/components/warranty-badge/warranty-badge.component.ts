import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-warranty-badge',
  templateUrl: './warranty-badge.component.html',
  imports: [CommonModule],
  styleUrls: ['./warranty-badge.component.scss']
})
export class WarrantyBadgeComponent implements OnInit {

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    
  }
}