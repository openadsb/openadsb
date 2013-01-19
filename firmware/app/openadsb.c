// Mode-S receiver by KJ6MEL
// Adapted from LUFA and http://nonolithlabs.com (C) 2011 Kevin Mehall (Nonolith Labs) <km@kevinmehall.net>
// Licensed under the terms of the GNU GPLv3+

#include "openadsb.h"

#define BOOTLOADER_JUMP_ADDR	0x4ff8

#define LED_PORT PORTB	
#define RED_LED_PIN 0
#define GREEN_LED_PIN 1

#define VCC_EN_PORT PORTC
#define VCC_EN_PIN 2

#define TIMEOUT		15625	//500 msec

#ifndef MIN
#define MIN(a, b)	((a) < (b) ? (a) : (b))
#endif

//unsigned int timer = 15625; // 500ms
unsigned char bulkdatain[64];
unsigned char bulkdataout[64];

// buf contents: AA AA BB BB CC DD EE FF GG HH II JJ ....
// A - RX level
// B - DAC level
// C - bad short pkts 
// D - bad long pkts
// E - reserved
// F - reserved
// G,H,I,... - data bytes
unsigned char adsb_buf[24];	// bk - for use in adsb.asm

// fixme - add counters accessible from asm file, report them in streaming output
uint8_t bad_short_pkts;
uint8_t bad_long_pkts;
uint8_t overflow_cnt;
uint16_t rx_level;


#if defined (CDC_MODE)
/** Contains the current baud rate and other settings of the virtual serial port. While this demo does not use
 *  the physical USART and thus does not use these settings, they must still be retained and returned to the host
 *  upon request or the host will assume the device is non-functional.
 *
 *  These values are set by the host via a class-specific request, however they are not required to be used accurately.
 *  It is possible to completely ignore these value or use other settings as the host is completely unaware of the physical
 *  serial link characteristics and instead sends and receives data in endpoint streams.
 */
static CDC_LineEncoding_t LineEncoding = { .BaudRateBPS = 0,
                                           .CharFormat  = CDC_LINEENCODING_OneStopBit,
                                           .ParityType  = CDC_PARITY_None,
                                           .DataBits    = 8                            };
#endif

extern unsigned char decode_adsb(void);	// implemented in asm
void setDac(uint16_t val);
uint16_t getADC(void);
void adcStart(void);
uint8_t adcResultReady(void);

uint8_t readSignatureVal(val)
{
}

// Fixme - need different configuration for CDC mode vs custom mode
void configureEndpoint(void){
#if defined (CDC_MODE)
	USB_ep_in_init(CDC_TX_EPNUM, USB_EP_TYPE_BULK_gc, CDC_TXRX_EPSIZE);
	USB_ep_in_start(CDC_TX_EPNUM, bulkdatain, 64);		// fixme - do we need this?
	
	USB_ep_in_init(CDC_NOTIFICATION_EPNUM, USB_EP_TYPE_BULK_gc, CDC_TXRX_EPSIZE);
	USB_ep_in_start(CDC_NOTIFICATION_EPNUM, bulkdatain, 64);		
	
	USB_ep_out_init(CDC_RX_EPNUM, USB_EP_TYPE_BULK_gc, CDC_TXRX_EPSIZE);
	USB_ep_out_start(CDC_RX_EPNUM, bulkdataout);
#else
	USB_ep_in_init(1, USB_EP_TYPE_BULK_gc, 64);
	USB_ep_in_start(1, bulkdatain, 64);		// fixme - do we need this?
	
	USB_ep_out_init(2, USB_EP_TYPE_BULK_gc, 64);
	USB_ep_out_start(2, bulkdataout);
#endif
}

uint8_t outcntr = 0;

// Fixme - need different configuration for CDC mode vs custom mode
void pollEndpoint(void){	
#if defined (CDC_MODE)
	if (USB_ep_out_received(CDC_RX_EPNUM)){
		USB_ep_out_start(CDC_RX_EPNUM, bulkdataout);
		outcntr++;
	}
#else
	if (USB_ep_out_received(2)){
		USB_ep_out_start(2, bulkdataout);
		outcntr++;
	}
#endif
}

unsigned int dacval = 0;

int main(void){
	unsigned int nbytes;
	unsigned boot_delay = 5;	// 5 sec
	volatile unsigned int i, j;
	uint8_t tx_pending = 0;

	SetupHardware();
	//sei();
	//setDac(0x900);	// about 3.2V output, ~1.3V at output filter.	0x800 is about lowest
	//dacval = 0x7a0;
	dacval = 0x950;
	setDac(dacval);	// about 3.2V output, ~1.3V at output filter.	0x800 is about lowest

	configureEndpoint();

	// Setup TTC0 as our timeout counter - 500msec
	TCC0.CTRLA = TC_CLKSEL_DIV1024_gc; // 31.25KHz = 0.032ms
	TCC0.PERH = (TIMEOUT>>8);
	TCC0.PERL = (TIMEOUT&0xFF);
	TCC0.CNT = 0;		// set timeout prior to calling decode_adsb()

	adcStart();		// kick start the ADC reads

	while (1){	
		unsigned int num;
		//while(!(TCC0.INTFLAGS & TC0_OVFIF_bm)) { 

		USB_Task();
		pollEndpoint();

		if(USB_DeviceState == DEVICE_STATE_Configured) {

			// do all this only if we have space in the buffer for a new packet
			if(USB_ep_in_sent(1)) {
				// start ADC conversion of RX level
				//if(adcResultReady()) {
					rx_level = getADC();
					//dacval = rx_level + 0x1c5;
					//setDac(dacval);
					adcStart();
				//}
				
				// clear old packet data
				for(j=0; j<sizeof(adsb_buf); j++)
					adsb_buf[j] = 0;
				

				// set timeout prior to calling decode_adsb()
				TCC0.CNT = 0;		
				TCC0.INTFLAGS = TC0_OVFIF_bm;
				
				// try to get a packet
				num = decode_adsb();	// will return on timeout or rx packet

				//LED_PORT.OUTSET = (1<<GREEN_LED_PIN);		// Green OFF
				if(num) {
					//if(tx_pending && !USB_ep_in_sent(1)) {			
					if(!USB_ep_in_sent(1)) {			
						// skip if still waiting for other packets - overflow
						overflow_cnt++;			// fixme - useless
					} 
					else {	
						// fixme - remove this header - use setup packet instead
						adsb_buf[0] = rx_level >> 8;
						adsb_buf[1] = rx_level & 0xff;
						adsb_buf[2] = dacval >> 8;
						adsb_buf[3] = dacval & 0xff;
						adsb_buf[4] = bad_short_pkts;
						adsb_buf[5] = bad_long_pkts;
						adsb_buf[6] = 0;
						adsb_buf[7] = 0;
						num += 8;	

						// reset pkt error counters
						bad_short_pkts = bad_long_pkts = 0;

						LED_PORT.OUTTGL = (1<<RED_LED_PIN);	// toggle LED
						USB_ep_in_start(1, adsb_buf, num);	
						tx_pending = 1;
						//while(--timeout && !USB_ep_in_sent(1));		// wait for sent
						//while(!USB_ep_in_sent(1));		// wait for sent
					}
				}
				else {
					USB_ep_in_start(1, bulkdatain, 0);	// ZLP
				}
			}
			//setDac(dacval);
			//dacval = (dacval+16) % 0xFFF;
		}
		//LED_PORT.OUTSET = (1<<GREEN_LED_PIN);	// LED off
		//LED_PORT.OUTTGL = (1<<GREEN_LED_PIN);	// toggle LED
		//LED_PORT.OUTTGL = (1<<RED_LED_PIN);	// toggle LED
	}
}


void setDac(uint16_t val)
{
	DACB.CH0DATAH = (val >> 8) & 0x0F;
	DACB.CH0DATAL = val & 0xFF;
}

uint16_t getADC(void)
{
	uint16_t result;
	result = ADCA.CH0RES;
	ADCA.CH0.INTFLAGS = ADC_CH_CHIF_bm;	// clear complete flag
	return result;
}

void adcStart(void)
{
	ADCA.CH0.CTRL |= ADC_CH_START_bm;
}

uint8_t adcResultReady(void)
{
	if(ADCA.CH0.INTFLAGS & ADC_CH_CHIF_bm)
		return true;
	else 
		return false;
}

/** Configures the board hardware and chip peripherals for the project's functionality. */
void SetupHardware(void){
	// GPIO ports
	LED_PORT.OUTSET = (1<<RED_LED_PIN);				// Red OFF
	LED_PORT.OUTCLR = (1<<GREEN_LED_PIN);				// Green ON
	VCC_EN_PORT.OUTSET = (1<<VCC_EN_PIN);				// VCC_FE enabled
	LED_PORT.DIRSET = (1<<RED_LED_PIN) | (1<<GREEN_LED_PIN);	// LEDs 
	VCC_EN_PORT.DIRSET = (1<<VCC_EN_PIN);				// VCC_FE_EN
	
	// DAC on PB2
	DACB.CTRLA = 0x1;	// enable DAC, no output
	DACB.CTRLB = DAC_CHSEL_SINGLE_gc;
	DACB.CTRLC = DAC_REFSEL_AVCC_gc;
	DACB.TIMCTRL = DAC_CONINTVAL_128CLK_gc | DAC_REFRESH_256CLK_gc;
	DACB.CH0DATAH = 0x00;
	DACB.CH0DATAL = 0x00;
	DACB.CH1DATAH = 0;
	DACB.CH1DATAL = 0;
	DACB.CH0OFFSETCAL = 0;
	DACB.CH0GAINCAL = 127;
	DACB.CTRLA = 0x5;	// enable DAC ch0

	// AC - Use AC0 on Port A
	PORTA.DIRCLR = 3;		// pins 0, 1 inputs
	PORTA.PIN0CTRL = (3<<0);	// disable digital input on this port
	//ACA.AC0CTRL = AC_HSMODE_bm | AC_ENABLE_bm | (1<<1);	// small hysteresis
	ACA.AC0CTRL = AC_HSMODE_bm | AC_ENABLE_bm | (2<<1);	// large hysteresis		
	ACA.AC0MUXCTRL = (1<<3);	// pos=PA1 (AC1), neg=PA0 (AC0)
	//ACA.AC0MUXCTRL = (1<<3) | (5);	// pos=PA1 (AC1), neg=DAC
	ACA.CTRLA = AC_AC0OUT_bm;	// output on PA7

#if 1
	// ADCA on PA0
	ADCA.CTRLA |= 1;			// enable ADC, no DMA
	ADCA.CTRLB = 0x18;		// signed mode, 12 bit, freerunning
	//ADCA.CTRLB = ADC_RESOLUTION_12BIT_gc;		// signed mode, 12 bit, freerunning
	ADCA.REFCTRL = ADC_REFSEL_VCCDIV2_gc | ADC_BANDGAP_bm;
	//ADCA.REFCTRL = ADC_REFSEL_INT1V_gc | 0x02;
	ADCA.PRESCALER = ADC_PRESCALER_DIV8_gc;
	//ADCA.CALL = 			// fixme - read from sig row
	//ADCA.CALH = 
	//ADCA.CH0.CTRL = ADC_CH_INPUTMODE_SINGLEENDED_gc;	// gain=1
	ADCA.CH0.CTRL = ADC_CH_INPUTMODE_DIFFWGAIN_gc;	// gain=1
	//ADCA.CH0.CTRL = ADC_CH_GAIN_DIV2_gc | ADC_CH_INPUTMODE_DIFFWGAIN_gc;	// gain=1/2
	ADCA.CH0.MUXCTRL = ADC_CH_MUXPOS_PIN0_gc | 5;	// PA0, pad ground
	
	// vref = vcc/2 = 1.65V. adc = -vref/gain to +vref/gain (12 bit).  for 0 to +vref (11 bit), 
	// for gain = 1: -1.65V to +1.65V.  0x6c6 = 1734 = 1734/4096 * vref = 699mV - very close to 700mV measured
	// if gain = 1/2: -3.3V to +3.3V.  
#endif
	// SPI on PC[4:7]
	// for now just keep SS# deasserted
	PORTC.OUTSET = (1<<4);		// SS#
	PORTC.OUTCLR = (1<<5);		// MOSI
	PORTC.OUTCLR = (1<<7);		// SCK
	PORTC.DIRSET = (1<<4)|(1<<5)|(1<<7);	// MOSI/SS#/SCK outputs

	// USB
	USB_ConfigureClock();
	USB_Init();

	// CLKOUT on PC7 (muxed with SCK) - for measuring osc accuracy
	PORTCFG_CLKEVOUT = PORTCFG_CLKOUT_PC7_gc | PORTCFG_CLKOUTSEL_CLK1X_gc;	
	
}

/** Event handler for the library USB Control Request reception event. */
bool EVENT_USB_Device_ControlRequest(USB_Request_Header_t* req){
#if defined (CDC_MODE)
	if (req->bRequest == CDC_REQ_GetLineEncoding && req->bmRequestType == (REQDIR_DEVICETOHOST | REQTYPE_CLASS | REQREC_INTERFACE)) {
		unsigned char num = MIN(sizeof(ep0_buf_in), sizeof(LineEncoding));
		memcpy(ep0_buf_in, &LineEncoding, num);
		USB_ep0_send(num);
		return true;
	}
	else if (req->bRequest == CDC_REQ_SetLineEncoding && req->bmRequestType == (REQDIR_HOSTTODEVICE | REQTYPE_CLASS | REQREC_INTERFACE)) {
		// fixme - read from setup stream? or this packet?
		USB_ep0_send(0);
		return true;
	}
	else if (req->bRequest == CDC_REQ_SetControlLineState && req->bmRequestType == (REQDIR_HOSTTODEVICE | REQTYPE_CLASS | REQREC_INTERFACE)) {
		USB_ep0_send(0);
		return true;
	}
	return false;
#else
	if ((req->bmRequestType & CONTROL_REQTYPE_TYPE) == REQTYPE_VENDOR){
		if (req->bRequest == 0x23){
			ep0_buf_in[0] = outcntr;
			ep0_buf_in[1] = bulkdataout[0];
			ep0_buf_in[2] = endpoints[2].out.CNTL;
			ep0_buf_in[3] = endpoints[2].out.STATUS;
			USB_ep0_send(4);
			return true;
		}else if (req->bRequest == 0x24){
			USB_ep_out_init(2, USB_EP_TYPE_BULK_gc, 64);
			USB_ep_out_start(2, bulkdataout);
			outcntr = 0;
			USB_ep0_send(0);
		}else if (req->bRequest == 0x25){
			// Request Counters
			ep0_buf_in[0] = rx_level >> 8;
			ep0_buf_in[1] = rx_level & 0xff;
			ep0_buf_in[2] = dacval >> 8;
			ep0_buf_in[3] = dacval & 0xff;
			ep0_buf_in[4] = bad_short_pkts;
			ep0_buf_in[5] = bad_long_pkts;
			ep0_buf_in[6] = overflow_cnt;
			bad_short_pkts = 0;		// reset counter
			bad_long_pkts = 0;		// reset counter
			overflow_cnt = 0;		// reset counter
			USB_ep0_send(7);
			return true;
		}else if (req->bRequest == 0xDA){
			// Set DAC
			dacval = req->wValue;
			setDac(dacval);
			USB_ep0_send(0);
			return true;
		}else if (req->bRequest == 0xBB){
			// Goto Bootloader
			USB_ep0_send(0);
			USB_ep0_wait_for_complete();
			LED_PORT.OUTCLR = (1<<RED_LED_PIN);
			_delay_us(10000);
			USB_Detach();
			_delay_us(100000);
			cli();
			void (*enter_bootloader)(void) = BOOTLOADER_JUMP_ADDR/2;
			enter_bootloader();
		}
	}
	
	return false;
#endif
}


